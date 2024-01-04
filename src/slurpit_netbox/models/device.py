from django.db import models
from dcim.models import Device, DeviceType

"""
"id": "612",
"hostname": "SW-PLC-33.amphia.zh",
"fqdn": "10.64.144.31",
"device_os": "cisco_ios",
"device_type": "CATALYST 4510R+E",
"disabled": "0",
"added": "finder",
"last_seen": "2023-11-02 00:00:43",
"createddate": "2023-10-30 13:29:17",
"changeddate": "2023-11-01 23:02:51"
"""

from netbox.models import NetBoxModel


digest_parts = 'hostname', 'fqdn', 'device_os', 'brand', 'disabled'
fmt_digest = '\x01'.join((f"{{{part}}}" for part in digest_parts))
mapped_in = dict(null=True, on_delete=models.SET_NULL)


class StagedDevice(NetBoxModel):
    digest = models.TextField(max_length=64, unique=True)
    hostname = models.TextField(max_length=255, unique=True)
    fqdn = models.TextField(max_length=128)
    device_os = models.TextField(max_length=128)
    device_type = models.TextField(max_length=255)
    brand = models.TextField(max_length=255)
    disabled = models.IntegerField()
    added = models.TextField(max_length=32)
    last_seen = models.DateTimeField(null=True)
    createddate = models.DateTimeField()
    changeddate = models.DateTimeField(null=True)
    location = models.TextField(max_length=128, null=True)
    region = models.TextField(max_length=128, null=True)
    rack = models.TextField(max_length=128, null=True)
    position = models.TextField(max_length=128, null=True)
    airflow = models.TextField(max_length=128, null=True)
    latitude = models.DecimalField(max_digits=8, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=8, decimal_places=6, null=True)
    tenant = models.TextField(max_length=128, null=True)
    description = models.TextField(max_length=256, null=True)

    def __str__(self):
        return f"{self.hostname}"
    
    
class ImportedDevice(NetBoxModel):
    digest = models.TextField(max_length=64, unique=True)
    hostname = models.TextField(max_length=255, unique=True)
    fqdn = models.TextField(max_length=128)
    device_os = models.TextField(max_length=128)
    device_type = models.TextField(max_length=255)
    brand = models.TextField(max_length=255)
    disabled = models.IntegerField()
    added = models.TextField(max_length=32)
    last_seen = models.DateTimeField(null=True)
    createddate = models.DateTimeField()
    changeddate = models.DateTimeField(null=True)
    mapped_devicetype = models.ForeignKey(to=DeviceType, **mapped_in)
    mapped_device = models.ForeignKey(to=Device, **mapped_in)
    location = models.TextField(max_length=128, null=True)
    region = models.TextField(max_length=128, null=True)
    rack = models.TextField(max_length=128, null=True)
    position = models.TextField(max_length=128, null=True)
    airflow = models.TextField(max_length=128, null=True)
    latitude = models.DecimalField(max_digits=8, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=8, decimal_places=6, null=True)
    tenant = models.TextField(max_length=128, null=True)
    description = models.TextField(max_length=256, null=True)

    def get_absolute_url(self):
        return '/'
    
    def __str__(self):
        return f"{self.hostname}"
    
    @property
    def slurpit_device_type(self):
        # Returns the 'slurpit_devicetype' value from the mapped_device's custom_field_data or None if not present.
        return self.mapped_device.custom_field_data.get('slurpit_devicetype')
