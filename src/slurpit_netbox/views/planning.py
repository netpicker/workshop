from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from ..tables import PlanningTable
from ..models import Source


@register_model_view(Source, name='planning', path='planning')
class PlanningListView(generic.ObjectListView):
    table = PlanningTable

    tab = ViewTab(
        label="Planning",
        # badge=lambda obj: IPFabricBranch.objects.filter(sync=obj).count(),
        permission="slurpit_netbox.view_planning",
    )

    def get_queryset(self, request):
        from ..models import Planning
        queryset = Planning.objects.all()
        return queryset

    def get(self, request, **kwargs):
        return super().get(request)