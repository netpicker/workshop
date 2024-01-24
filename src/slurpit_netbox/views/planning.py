from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import slugify
from django.urls import clear_url_caches, get_resolver, reverse
from dcim.models import Device
from netbox.registry import registry
from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from ..tables import PlanningTable
from ..models import SlurpitSource
from ..models import SlurpitPlanning

from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator

import sys
from django.conf import settings


def reload_urlconf():
    url_conf = settings.ROOT_URLCONF
    if sys.modules.get(url_conf):
        clear_url_caches()
        del sys.modules[url_conf]


@register_model_view(SlurpitSource, name='planning', path='planning')
@method_decorator(slurpit_plugin_registered, name='dispatch')
class PlanningListView(generic.ObjectChildrenView):
    queryset = SlurpitSource.objects.all()
    child_model = SlurpitPlanning
    template_name = "slurpit_netbox/planning/planning_list.html"
    table = PlanningTable
    actions = []

    tab = ViewTab(
        label="Planning",
        permission="slurpit_netbox.view_planning",
    )

    def get_children(self, request, parent):
        return self.child_model.objects.filter(source=parent)

    def post(self, request, *args, **kwargs):
        pks = request.POST.getlist('pk')
        source_id = request.resolver_match.kwargs['pk']
        SlurpitPlanning.update_selected_for(source_id, pks)
        planning = SlurpitPlanning.get_planning()
        make_planning_tabs(planning)
        return redirect(self.get_return_url(request))

    def get_return_url(self, request, obj=None):
        return reverse('plugins:slurpit_netbox:source_planning',
                       kwargs=request.resolver_match.kwargs)


def make_planning_tabs(plannings):
    def create_view_class(planning: SlurpitPlanning):
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

    app_label = Device._meta.app_label
    model_name = Device._meta.model_name
    entry = registry['views'][app_label][model_name]
    prefix = 'slurpit_'
    if entry:
        present = [v for v in entry if v['name'].startswith(prefix)]
        for v in present:
            entry.remove(v)
    for planning in plannings:
        slug = slugify(planning.name)
        name = f"{prefix}{slug}"
        deco = register_model_view(Device, name=name, path=slug)
        view_class = create_view_class(planning)
        deco(view_class)


@register_model_view(SlurpitSource, name='fetch_planning', path='fetch')
class PlanningSyncView(generic.ObjectView):
    queryset = SlurpitSource.objects

    def post(self, request, *args, **kwargs):
        source = get_object_or_404(SlurpitSource.objects, **kwargs)
        SlurpitPlanning.sync(source)
        planning = SlurpitPlanning.get_planning()
        make_planning_tabs(planning)
        url = reverse('plugins:slurpit_netbox:source_planning',
                       kwargs=request.resolver_match.kwargs)
        return redirect(url)
