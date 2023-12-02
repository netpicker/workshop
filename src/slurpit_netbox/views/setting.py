from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View
from extras.choices import ChangeActionChoices
from netbox.staging import StagedChange
from netbox.views import generic
from netbox.views.generic.base import BaseObjectView
from utilities.forms import ConfirmationForm
from utilities.htmx import is_htmx
from utilities.utils import count_related
from utilities.utils import get_viewname
from utilities.utils import serialize_object
from utilities.utils import shallow_compare_dict
from utilities.views import register_model_view
from utilities.views import ViewTab

# from .filtersets import BranchFilterSet
# from .filtersets import SnapshotFilterSet
from ..filtersets import SourceFilterSet
# from .filtersets import StagedChangeFilterSet
# from .forms import BranchFilterForm
# from .forms import RelationshipFieldForm
# from .forms import SnapshotFilterForm
from ..forms import SourceFilterForm, SourceForm
# from .forms import SourceForm
# from .forms import SyncForm
# from .forms import TransformFieldForm
# from .forms import TransformMapForm
# from .models import Branch
# from .models import RelationshipField
# from .models import Snapshot
from ..models import Source
# from .models import Sync
# from .models import TransformField
# from .models import TransformMap
# from .tables import BranchTable
# from .tables import RelationshipFieldTable
# from .tables import SnapshotTable
from ..tables import SourceTable
# from .tables import TransformFieldTable
# from .tables import TransformMapTable
# from .tables import StagedChangesTable


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
            r = source.get_session().get('/api/devices')
            status = f"{'OK' if r.ok else 'ERR'} ({r.status_code})"
            return HttpResponse(status)
        return super().get(request, **kwargs)

    # def get_extra_context(self, request, instance):
    #     from ..models import Planning
    #     planning = Planning.objects.filter(source=instance, disabled=False)
    #     data = dict(planning=planning)
    #     return data
    #     related_models = (
    #         (
    #             IPFabricSnapshot.objects.restrict(request.user, "view").filter(
    #                 source=instance
    #             ),
    #             "source_id",
    #         ),
    #     )
    #     job = instance.jobs.order_by("id").last()
    #     data = {"related_models": related_models, "job": job}
    #     if job:
    #         data["job_results"] = job.data
    #     return data


@register_model_view(Source, "sync")
class SourceSyncView(BaseObjectView):
    queryset = Source.objects.all()

    def get_required_permission(self):
        return "ipfabric_netbox.sync_source"

    def get(self, request, pk):
        ipfabricsource = get_object_or_404(self.queryset, pk=pk)
        return redirect(ipfabricsource.get_absolute_url())

    def post(self, request, pk):
        ipfabricsource = get_object_or_404(self.queryset, pk=pk)
        job = ipfabricsource.enqueue_sync_job(request=request)

        messages.success(request, f"Queued job #{job.pk} to sync {ipfabricsource}")
        return redirect(ipfabricsource.get_absolute_url())


@register_model_view(Source, "delete")
class SourceDeleteView(generic.ObjectDeleteView):
    queryset = Source.objects.all()


class SourceBulkDeleteView(generic.BulkDeleteView):
    queryset = Source.objects.all()
    filterset = SourceFilterSet
    table = SourceTable
