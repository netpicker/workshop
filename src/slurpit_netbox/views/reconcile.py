from netbox.views import generic

from ..models import ImportedDevice
from .. import forms, importer, models, tables

class ReconcileView(generic.ObjectListView):
    queryset = models.ImportedDevice.objects
    table = tables.ImportedDeviceTable