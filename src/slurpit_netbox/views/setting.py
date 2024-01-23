from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from netbox.views import generic
from netbox.views.generic.base import BaseObjectView
from utilities.htmx import is_htmx
from utilities.views import register_model_view, ViewTab
from django.views.generic import View
from ..filtersets import SourceFilterSet
from ..forms import SourceFilterForm, SourceForm, SlurpitPlanTableForm, SlurpitApplianceTypeForm
from ..models import Source, Setting, SlurpitLog, PlanningDataTab, SlurpitPlan, Snapshot
from ..tables import SourceTable, SlurpitPlanTable
from ..management.choices import *
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from ..utilities import generate_random_string
from users.models import ObjectPermission, Token
from dcim.models import Device
from dcim.views import DeviceComponentsView
from django.db.models.query import QuerySet
from django.core.cache import cache
import requests
from django_tables2 import RequestConfig, tables, Column
from utilities.paginator import EnhancedPaginator, get_paginate_count
from ..importer import get_latest_data_on_planning
from django.urls import reverse
from django.http import HttpResponseRedirect
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.http import JsonResponse
from account.models import UserToken
from django.conf import settings

BATCH_SIZE = 128

def split_list(input_list, chunk_size):
    # For item i in a range that is a length of input_list,
    for i in range(0, len(input_list), chunk_size):
        # Create an index range for l of n items:
        yield input_list[i:i + chunk_size]

@method_decorator(slurpit_plugin_registered, name='dispatch')
class SourceListView(generic.ObjectListView):
    queryset = Source.objects
    filterset = SourceFilterSet
    filterset_form = SourceFilterForm
    table = SourceTable

@method_decorator(slurpit_plugin_registered, name='dispatch')
@register_model_view(Source, "edit")
class SourceEditView(generic.ObjectEditView):
    queryset = Source.objects.all()
    form = SourceForm


@register_model_view(Source)
class SourceView(generic.ObjectView):
    queryset = Source.objects.all()

    def get(self, request, **kwargs):
        if is_htmx(request):
            source: Source = self.get_object(**kwargs)
            r = source.get_session().get('/platform/ping')
            status = f"{'OK' if r.ok else 'ERR'} ({r.status_code})"
            return HttpResponse(status)
        return super().get(request, **kwargs)


@register_model_view(Source, "sync", path="sync")
class SourceSyncView(BaseObjectView):
    queryset = Source.objects.all()

    def get_required_permission(self):
        return "slurpit_netbox.sync_source"

    def get(self, request, pk):
        from ..models import Planning
        source = get_object_or_404(self.queryset, pk=pk)
        Planning.sync(source)
        messages.success(request, f"Planning sync'ed")
        return redirect(source.get_absolute_url())


@register_model_view(Source, "delete")
@method_decorator(slurpit_plugin_registered, name='dispatch')
class SourceDeleteView(generic.ObjectDeleteView):
    queryset = Source.objects.all()


@method_decorator(slurpit_plugin_registered, name='dispatch')
class SourceBulkDeleteView(generic.BulkDeleteView):
    queryset = Source.objects.all()
    filterset = SourceFilterSet
    table = SourceTable

@method_decorator(slurpit_plugin_registered, name='dispatch')
class SettingsView(View):
    
    app_label = "dcim"
    model_name = "device"
    
    def get(self, request):
        appliance_type = ''
        try:
            setting = Setting.objects.get()
            server_url = setting.server_url
            api_key = setting.api_key
            appliance_type = setting.appliance_type

        except Exception as e:
            setting = None
            
        push_api_key = ''
        
        if setting is None:
            connection_status = ''
        else:
            connection_status = setting.connection_status

        tokens = UserToken.objects.filter(user=request.user).count()

        if tokens > 0:
            push_api_key = 'existed'
        
        tab_param = request.GET.get('tab', None)
        plannings = []
        slurpit_apis = []
        initial_data = {
            "appliance_type": appliance_type
        }

        form = SlurpitApplianceTypeForm(initial=initial_data)

        if tab_param == 'data_tabs':
            # Synchronize planning data
            sync_param = request.GET.get('sync', None)
            if sync_param == 'true':
                # Get planning data from Slurpit API
                new_plannings = []
                if setting is not None:
                    new_plannings = self.get_planning_list(request, server_url, api_key)

                new_items = []
                for item in new_plannings:
                    new_items.append(
                        SlurpitPlan(name=item['name'], plan_id=item['id'])
                    )
                
                split_plans_arr = list(split_list(new_items, BATCH_SIZE))

                for plan_arr in split_plans_arr:
                    SlurpitPlan.objects.bulk_create(plan_arr, batch_size=BATCH_SIZE, ignore_conflicts=True)

            plannings = SlurpitPlan.objects.all().order_by('id')
            
        else:   
            appliance_type_param = request.GET.get('appliance_type', None)

            if appliance_type_param:
                if setting is None:
                    setting = Setting.objects.create()
                # Update appliance typ
                setting.appliance_type = appliance_type_param
                setting.save()

                return HttpResponseRedirect(reverse("plugins:slurpit_netbox:settings"))

            slurpit_apis = [
                {
                    "type": "POST",
                    "url": "api/plugins/slurpit/snapshot/"
                },
                {
                    "type": "DELETE",
                    "url": "api/plugins/slurpit/snapshot/delete-all/{hostname}/{planning_id}/"
                },
                {
                    "type": "POST",
                    "url": "api/plugins/slurpit/planning/"
                },
                {
                    "type": "DELETE",
                    "url": "api/plugins/slurpit/planning/delete/{planning_id}/"
                },
                {
                    "type": "DELETE",
                    "url": "api/plugins/slurpit/planning/delete-all/"
                },
                {
                    "type": "POST",
                    "url": "api/plugins/slurpit/device/"
                },
                {
                    "type": "DELETE",
                    "url": "api/plugins/slurpit/device/delete/{hostname}/"
                },
                {
                    "type": "DELETE",
                    "url": "api/plugins/slurpit/device/delete-all/"
                },
                {
                    "type": "GET",
                    "url": "api/plugins/slurpit/test/api/"
                }
            ]

            test_param = request.GET.get('test',None)
            if test_param =='test':
                if setting is None:
                    log_message = "Slurpit API test is failded."
                    SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.SETTING, message=log_message)
                    messages.warning(request, "You can not test. To use the Slurp'it plugin you should first configure the server settings. Go to settings and configure the Slurp'it server in the parameter section.")
                else:
                    connection_status = self.connection_test(request, server_url, api_key)
                    setting.connection_status = connection_status
                    setting.save()
                    log_message = f"Slurpit API's test result is {connection_status}."
                    SlurpitLog.objects.create(level=LogLevelChoices.LOG_INFO, category=LogCategoryChoices.SETTING, message=log_message)

            action_param = request.GET.get('action',None)
            if action_param == 'generate':
                if setting is None:
                    setting = Setting.objects.create()

                token, __annotations__ = Token.objects.get_or_create(user=request.user)
                push_api_key = Token.generate_key()
                token.key = push_api_key
                token.save()
                setting.push_api_key = push_api_key
                setting.save()


                log_message = f"Slurpit Push API is generated."
                SlurpitLog.objects.create(level=LogLevelChoices.LOG_INFO, category=LogCategoryChoices.SETTING, message=log_message)
        
        debug = settings.DEBUG
        return render(
            request,
            "slurpit_netbox/settings.html",
            {
                "setting": setting, 
                "connection_status": connection_status,
                "push_api_key": push_api_key,
                "plannings": plannings,
                "slurpit_apis": slurpit_apis,
                "form": form,
                "appliance_type": appliance_type,
                "debug": debug,
            },
        )
    
    def post(self, request):
        return_url = request.GET.get('return_url', None)
        if return_url is None:
            id = request.POST.get('setting_id')
            server_url = request.POST.get('server_url')
            api_key = request.POST.get('api_key')
            if id == "":
                obj, created = Setting.objects.get_or_create(id=0, defaults={'server_url': server_url, 'api_key': api_key})
            else:
                obj, created = Setting.objects.get_or_create(id=id, defaults={'server_url': server_url, 'api_key': api_key})
            log_message = "Added the settings parameter successfully."

            connection_status = self.connection_test(request, server_url, api_key)
            obj.connection_status = connection_status

            if not created:
                obj.server_url = server_url
                obj.api_key = api_key
                log_message = "Updated the settings parameter successfully."
                messages.success(request, "Updated the settings parameter successfully.")
            obj.save()
            
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.SETTING, message=log_message)
        else:
            plans = request.POST.getlist('pk')
            total_plan_ids = []

            # Split id: 1#plan_name
            for plan in plans:
                plan_arr = plan.split('#')
                total_plan_ids.append(plan_arr[0])
                
            SlurpitPlan.objects.filter(id__in=total_plan_ids).update(selected=True)
            SlurpitPlan.objects.exclude(id__in=total_plan_ids).update(selected=False)

            return redirect(return_url)
        
        return redirect(request.path)


    def connection_test(self, request, server_url, api_key):
        headers = {
                    'authorization': api_key,
                    'useragent': 'netbox/requests',
                    'accept': 'application/json'
                }
        connection_test = f"{server_url}/api/platform/ping"
        try:
            response = requests.get(connection_test, headers=headers)
        except Exception as e:
            messages.error(request, "Please confirm the Slurp'it server is running and reachable.")
            log_message ="Failed testing the connection to the Slurp'it server."          
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.SETTING, message=log_message)
            return "not connected"
        
        if response.status_code == 200:
            r = response.json()
            if r.get('status') == "up":
                log_message ="Tested the connection to the Slurp'it server successfully."        
                SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.SETTING, message=log_message)
                messages.success(request, "Tested the connection to the slurpit server successfully.")
            return 'connected'
        else:
            messages.error(request, "Failed testing the connection to the Slurp'it server.")
            log_message ="Failed testing the connection to the Slurp'it server."          
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.SETTING, message=log_message)
            return "not connected"
    
    def get_planning_list(self, request, server_url, api_key):
        headers = {
                    'authorization': api_key,
                    'useragent': 'netbox/requests',
                    'accept': 'application/json'
                }
        connection_test = f"{server_url}/api/planning"

        try:
            response = requests.get(connection_test, headers=headers)
        except Exception as e:
            messages.error(request, "Please confirm the Slurp'it server is running and reachable.")
            log_message ="Failed to get planning list of the Slurp'it server."          
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.SETTING, message=log_message)
            return []
        
        if response.status_code == 200:
            r = response.json()
            planning_list = []
            for plan in r:
                planning_list.append({
                    'id': plan['id'],
                    'name': plan['name']
                })
            
            return planning_list
        else:
            return []

def get_refresh_url(request, pk):
    get_params = request.GET.copy()
    get_params['refresh'] = 'none'
    get_params['sync'] = 'none'

    path = f"/dcim/devices/{pk}/Slurpit/"
    query_string = get_params.urlencode()
    url_no_refresh = f"{path}?{query_string}" if query_string else path

    return url_no_refresh


@register_model_view(Device, "Slurpit")
class SlurpitPlanning(View):
    template_name = "slurpit_netbox/planning_table.html"
    tab = ViewTab("Slurpit", permission="slurpit_netbox.view_devicetable")

    def get(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        form = (
            SlurpitPlanTableForm(request.GET)
            if "id" in request.GET
            else SlurpitPlanTableForm()
        )
        data = None
        cached_time = None
        result_status = "No Data"
        columns = []
        refresh = request.GET.get('refresh')
        sync = request.GET.get('sync')

        if form.is_valid():
            plan = form.cleaned_data["id"]
            result_type = request.GET.get('result_type')
            

            if result_type is None:
                result_type = "planning"

            cache_key = (
                f"slurpit_plan_{plan.plan_id}_{device.serial}_{result_type}"
            )

            url_no_refresh = get_refresh_url(request, pk)

            if sync == "sync":
                cache.delete(cache_key)
                temp = get_latest_data_on_planning(device.name, plan.plan_id)
                temp = temp[plan.name]["data"]

                Snapshot.objects.filter(hostname=device.name, plan_id=plan.plan_id).delete()

                # Store the latest data to DB
                new_items = []
                for item in temp:
                    new_items.append(
                        Snapshot(hostname=device.name, plan_id=plan.plan_id, content=item)
                    )
                
                split_devices_arr = list(split_list(new_items, BATCH_SIZE))

                for device_arr in split_devices_arr:
                    Snapshot.objects.bulk_create(device_arr, batch_size=BATCH_SIZE, ignore_conflicts=True)

                return HttpResponseRedirect(url_no_refresh)
            
            if refresh == "refresh":
                cache.delete(cache_key)
                return HttpResponseRedirect(url_no_refresh)

            try:
                cached_time, data = cache.get(cache_key)
                result_status = "Cached"
            except:
                pass
            if not data:
                data = []
                try: 
                    temp = Snapshot.objects.filter(hostname=device.name, plan_id=plan.plan_id)
                    result_key = f"{result_type}_result"

                    for r in temp:
                        r = r.content
                        raw = r[result_key]
                        data.append({**raw})
                    result_status = "Live"
                    cache.set(cache_key, (datetime.now(), data), 60 * 60 * 8)
                    
                except Exception as e:
                    messages.error(request, e)

        if refresh == "refresh":
            url_no_refresh = get_refresh_url(request, pk)
            return HttpResponseRedirect(url_no_refresh)
        
        if not data:
            data = []
        
        if len(data) > 0:
            raw = data[0]
            columns = list(raw.keys())
        
        columns = [(k, Column()) for k in columns]
        table = SlurpitPlanTable(data, extra_columns=columns)

        RequestConfig(
            request,
            {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            },
        ).configure(table)

        if is_htmx(request):
            return render(
                request,
                "htmx/table.html",
                {
                    "table": table,
                },
            )

        appliance_type = ''
        try:
            setting = Setting.objects.get()
            server_url = setting.server_url
            api_key = setting.api_key
            appliance_type = setting.appliance_type
        except ObjectDoesNotExist:
            setting = None

        return render(
            request,
            self.template_name,
            {
                "object": device,
                "tab": self.tab,
                "form": form,
                "table": table,
                "result_status": result_status,
                "cached_time": cached_time,
                'appliance_type': appliance_type,
            },
        )
