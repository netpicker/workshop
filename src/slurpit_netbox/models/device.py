from django.db import models
from dcim.models import Device


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


digest_parts = 'hostname', 'fqdn', 'device_os', 'disabled'
fmt_digest = '\x01'.join((f"{{{part}}}" for part in digest_parts))


class StagedDevice(NetBoxModel):
    digest = models.TextField(max_length=64, unique=True)
    hostname = models.TextField(max_length=255, unique=True)
    fqdn = models.TextField(max_length=128)
    device_os = models.TextField(max_length=128)
    device_type = models.TextField(max_length=255)
    disabled = models.IntegerField()
    added = models.TextField(max_length=32)
    last_seen = models.DateTimeField()
    createddate = models.DateTimeField()
    changeddate = models.DateTimeField()


class ImportedDevice(NetBoxModel):
    digest = models.TextField(max_length=64, unique=True)
    hostname = models.TextField(max_length=255, unique=True)
    fqdn = models.TextField(max_length=128)
    device_os = models.TextField(max_length=128)
    device_type = models.TextField(max_length=255)
    disabled = models.IntegerField()
    added = models.TextField(max_length=32)
    last_seen = models.DateTimeField()
    createddate = models.DateTimeField()
    changeddate = models.DateTimeField()

    mapped_device = models.ForeignKey(to=Device, null=True,
                                      on_delete=models.SET_NULL)

    def get_absolute_url(self):
        return '/'
