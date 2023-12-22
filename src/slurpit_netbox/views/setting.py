from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from netbox.views import generic
from netbox.views.generic.base import BaseObjectView
from utilities.htmx import is_htmx
from utilities.views import register_model_view
from django.views.generic import View
from ..filtersets import SourceFilterSet
from ..forms import SourceFilterForm, SourceForm
from ..models import Source, Setting, SlurpitLog
from ..tables import SourceTable
from ..management.choices import *
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator

import requests


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
    
    def get(self, request):
        try:
            setting = Setting.objects.get()
            server_url = setting.server_url
            api_key = setting.api_key
        except ObjectDoesNotExist:
            setting = None
            messages.warning(request, "To use the Slurp'it plugin you should first configure the server settings. Go to settings and configure the Slurp'it server in the parameter section.")
        
        if setting is None:
            connection_status = ''
        else:
            connection_status = setting.connection_status
            
        test_param = request.GET.get('test',None)
        if test_param =='test':
            if setting is None:
                messages.warning(request, "You can not test. To use the Slurp'it plugin you should first configure the server settings. Go to settings and configure the Slurp'it server in the parameter section.")
            else:
                connection_status = self.connection_test(request, server_url, api_key)
                setting.connection_status = connection_status
                setting.save()

        return render(
            request,
            "slurpit_netbox/settings.html",
            {"setting": setting, "connection_status": connection_status},
        )
    
    def post(self, request):
        id = request.POST.get('setting_id')
        server_url = request.POST.get('server_url')
        api_key = request.POST.get('api_key')
        if id == "":
            obj, created = Setting.objects.get_or_create(id=0, defaults={'server_url': server_url, 'api_key': api_key})
        else:
            obj, created = Setting.objects.get_or_create(id=id, defaults={'server_url': server_url, 'api_key': api_key})
        log_message = "Created the settings parameter successfully."
        
        if not created:
            obj.server_url = server_url
            obj.api_key = api_key
            obj.save()
            log_message = "Updated the settings parameter successfully."
            messages.success(request, "Updated the settings parameter successfully.")
        SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.SETTING, message=log_message)

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
            messages.error(request, "Please confirm Slurpit server is running now.")
            log_message ="Failed testing connection to the slurpit server."          
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.SETTING, message=log_message)
            return "not connected"
        
        if response.status_code == 200:
            r = response.json()
            if r.get('status') == "up":
                log_message ="Tested connection to the slurpit server successfully."        
                SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.SETTING, message=log_message)
                messages.success(request, "Tested connection to the slurpit server successfully.")
            return 'connected'
        else:
            messages.error(request, "Failed testing connection to the slurpit server.")
            log_message ="Failed testing connection to the slurpit server."          
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.SETTING, message=log_message)
            return "not connected"

        
        