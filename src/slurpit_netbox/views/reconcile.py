from netbox.views import generic

from ..models import SlurpitImportedDevice
from .. import forms, importer, models, tables
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator


@method_decorator(slurpit_plugin_registered, name='dispatch')
class ReconcileView(generic.ObjectListView):
    queryset = models.SlurpitImportedDevice.objects
    table = tables.SlurpitImportedDeviceTable
    template_name = "slurpit_netbox/comingsoon.html"