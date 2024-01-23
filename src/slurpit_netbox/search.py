from netbox.search import SearchIndex, register_search
from .models import SlurpitImportedDevice


@register_search
class SlurpitImportedDeviceIndex(SearchIndex):
    model = SlurpitImportedDevice
    fields = (
        ('hostname', 100),
        ('fqdn', 500),
    )
