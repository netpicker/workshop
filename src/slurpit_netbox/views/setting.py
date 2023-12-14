from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
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

class SourceListView(generic.ObjectListView):
    queryset = Source.objects
    filterset = SourceFilterSet
    filterset_form = SourceFilterForm
    table = SourceTable


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
class SourceDeleteView(generic.ObjectDeleteView):
    queryset = Source.objects.all()


class SourceBulkDeleteView(generic.BulkDeleteView):
    queryset = Source.objects.all()
    filterset = SourceFilterSet
    table = SourceTable


class SettingsView(View):
    
    def get(self, request):
        setting = Setting.objects.get()
        return render(
            request,
            "slurpit_netbox/settings.html",
            {"setting": setting},
        )
    
    def post(self, request):
        id = request.POST.get('setting_id')
        server_url = request.POST.get('server_url')
        api_key = request.POST.get('api_key')
        obj, created = Setting.objects.get_or_create(id=id, defaults={'server_url': server_url, 'api_key': api_key})
        log_message = "Created the settings parameter successfully."
        
        if not created:
            obj.server_url = server_url
            obj.api_key = api_key
            obj.save()
            log_message = "Updated the settings parameter successfully."
        
        SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.SETTING, message=log_message)

        return redirect(request.path)