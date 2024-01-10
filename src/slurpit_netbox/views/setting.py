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
from ..forms import SourceFilterForm, SourceForm, SlurpitPlanTableForm
from ..models import Source, Setting, SlurpitLog, PlanningDataTab, SlurpitPlan
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
        try:
            setting = Setting.objects.get()
            server_url = setting.server_url
            api_key = setting.api_key
        except ObjectDoesNotExist:
            setting = None
            
        if setting is None:
            connection_status = ''
            push_api_key = ''
        else:
            connection_status = setting.connection_status
            push_api_key = setting.push_api_key
        
        tab_param = request.GET.get('tab', None)
        plannings = []
        device_tab_paths = []

        if tab_param == 'data_tabs':
            plannings = self.get_planning_list(request, server_url, api_key)
            device_tab_paths = SlurpitPlan.objects.values_list('plan_id', flat=True)
            device_tab_paths = list(device_tab_paths)
        else:
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

        return render(
            request,
            "slurpit_netbox/settings.html",
            {
                "setting": setting, 
                "connection_status": connection_status,
                "push_api_key": push_api_key,
                "plannings": plannings,
                "device_tab_paths": device_tab_paths
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
            plans_arr = []
            # Split id: 1#plan_name
            for plan in plans:
                plan_arr = plan.split('#')
                total_plan_ids.append(plan_arr[0])
                plans_arr.append(
                    SlurpitPlan(name=plan_arr[1], plan_id=plan_arr[0], display=plan_arr[1])
                )
            # Remove unchecked plans.
            SlurpitPlan.objects.exclude(plan_id__in=total_plan_ids).delete()
            # Add checked new plans.
            split_plans_arr = list(split_list(plans_arr, BATCH_SIZE))

            for plan_arr in split_plans_arr:
                SlurpitPlan.objects.bulk_create(plan_arr, batch_size=BATCH_SIZE, ignore_conflicts=True)

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

@register_model_view(Device, "Slurpit")
class SlurpitPlanning(View):
    template_name = "slurpit_netbox/planning_table.html"
    tab = ViewTab("Slurpit", permission="slurpit_netbox.view_devicetable")

    def get(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        form = (
            SlurpitPlanTableForm(request.GET)
            if "plan_id" in request.GET
            else SlurpitPlanTableForm()
        )
        data = None
        columns = []
        if form.is_valid():
            plan = form.cleaned_data["plan_id"]

            cache_key = (
                f"slurpit_plan_{plan.plan_id}_{device.serial}"
            )
            cache.delete(cache_key)
            data = cache.get(cache_key)

            if not data:
                data = []
                try: 
                    temp = get_latest_data_on_planning(device.name, plan.plan_id)
                    temp = temp[plan.name]["data"]
                    print(data)
                    for r in temp:
                        raw = r['template_result']
                        data.append({**raw})
                        
                    # data = []
                    cache.set(cache_key, data, 60 * 60 * 8)
                    
                except Exception as e:
                    messages.error(request, e)

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


        return render(
            request,
            self.template_name,
            {
                "object": device,
                "tab": self.tab,
                "form": form,
                "table": table,
            },
        )
