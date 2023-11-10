from netbox.search import SearchIndex, register_search
from .models import ImportedDevice


@register_search
class ImportedDeviceIndex(SearchIndex):
    model = ImportedDevice
    fields = (
        ('hostname', 100),
        ('fqdn', 500),
    )
