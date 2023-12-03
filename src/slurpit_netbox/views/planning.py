from django.shortcuts import redirect
from django.urls import reverse
from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from ..tables import PlanningTable
from ..models import Source
from ..models import Planning


@register_model_view(Source, name='planning', path='planning')
class PlanningListView(generic.ObjectListView):
    template_name = 'slurpit_netbox/planning/object_list.html'
    table = PlanningTable

    tab = ViewTab(
        label="Planning",
        # badge=lambda obj: IPFabricBranch.objects.filter(sync=obj).count(),
        permission="slurpit_netbox.view_planning",
    )

    def get_queryset(self, request):
        queryset = Planning.objects.all()
        return queryset

    def get(self, request, **kwargs):
        return super().get(request)


class PlanningEditView(generic.BulkEditView):
    queryset = Planning.objects.all()

    def post(self, request, **kwargs):
        pks = request.POST.getlist('pk')
        source_id = request.resolver_match.kwargs['pk']
        Planning.update_selected_for(source_id, pks)
        return redirect(self.get_return_url(request))

    def get_return_url(self, request, obj=None):
        return reverse('plugins:slurpit_netbox:source_planning',
                       kwargs=request.resolver_match.kwargs)
