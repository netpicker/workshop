from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import slugify
from django.urls import reverse
from dcim.models import Device
from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from ..tables import PlanningTable
from ..models import Source
from ..models import Planning


# import sys
# from django.conf import settings
#
# def reload_urlconf(self):
#     if settings.ROOT_URLCONF in sys.modules:
#         reload(sys.modules[settings.ROOT_URLCONF])
#     return import_module(settings.ROOT_URLCONF)


@register_model_view(Source, name='planning', path='planning')
class PlanningListView(generic.ObjectChildrenView):
    queryset = Source.objects.all()
    child_model = Planning
    template_name = "slurpit_netbox/planning/planning_list.html"
    table = PlanningTable
    actions = []

    tab = ViewTab(
        label="Planning",
        # badge=lambda obj: IPFabricBranch.objects.filter(sync=obj).count(),
        permission="slurpit_netbox.view_planning",
    )

    def get_children(self, request, parent):
        return self.child_model.objects.filter(source=parent)

    def post(self, request, *args, **kwargs):
        pks = request.POST.getlist('pk')
        source_id = request.resolver_match.kwargs['pk']
        Planning.update_selected_for(source_id, pks)
        return redirect(self.get_return_url(request))

    def get_return_url(self, request, obj=None):
        return reverse('plugins:slurpit_netbox:source_planning',
                       kwargs=request.resolver_match.kwargs)


def make_planning_tabs(plannings):
    def create_view_class(planning: Planning):
        class SlurpitPlanningView(generic.ObjectView):
            _planning = planning
            queryset = Device.objects.all()
            template_name = "slurpit_netbox/lldp_neighbors.html"

        if planning.selected:
            SlurpitPlanningView.tab = ViewTab(
                label=planning.name,
                permission="dcim.slurpit_read_device",
                weight=3000
            )
        return SlurpitPlanningView

    for planning in plannings:
        slug = slugify(planning.name)
        deco = register_model_view(Device, name=f"slurpit_{slug}", path=slug)
        view_class = create_view_class(planning)
        deco(view_class)


@register_model_view(Source, name='fetch_planning', path='fetch')
class PlanningSyncView(generic.ObjectView):
    queryset = Source.objects

    def post(self, request, *args, **kwargs):
        source = get_object_or_404(Source.objects, **kwargs)
        Planning.sync(source)
        planning = Planning.get_planning()
        make_planning_tabs(planning)
        url = reverse('plugins:slurpit_netbox:source_planning',
                       kwargs=request.resolver_match.kwargs)
        return redirect(url)
