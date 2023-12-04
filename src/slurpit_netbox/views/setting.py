from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from netbox.views import generic
from netbox.views.generic.base import BaseObjectView
from utilities.htmx import is_htmx
from utilities.views import register_model_view
from ..filtersets import SourceFilterSet
from ..forms import SourceFilterForm, SourceForm
from ..models import Source
from ..tables import SourceTable


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
