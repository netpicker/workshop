from django.db import models
from dcim.models import Device, DeviceType

"""
"hostname": "SW-PLC-33.amphia.zh",
"fqdn": "10.64.144.31",
"device_os": "cisco_ios",
"device_type": "CATALYST 4510R+E",
"added": "finder",
"createddate": "2023-10-30 13:29:17",
"changeddate": "2023-11-01 23:02:51"
"""

from netbox.models import NetBoxModel, PrimaryModel

class SlurpitStagedDevice(NetBoxModel):
    slurpit_id = models.BigIntegerField (unique=True)
    disabled = models.BooleanField(default=False)
    hostname = models.CharField(max_length=255, unique=True)
    fqdn = models.CharField(max_length=128)
    ipv4 = models.CharField(max_length=23, null=True)
    device_os = models.CharField(max_length=128)
    device_type = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    createddate = models.DateTimeField()
    changeddate = models.DateTimeField()

    def __str__(self):
        return f"{self.hostname}"
    
    
class SlurpitImportedDevice(NetBoxModel):
    slurpit_id = models.BigIntegerField(unique=True)
    disabled = models.BooleanField(default=False)
    hostname = models.CharField(max_length=255, unique=True)
    fqdn = models.CharField(max_length=128)
    ipv4 = models.CharField(max_length=23, null=True)
    device_os = models.CharField(max_length=128)
    device_type = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    createddate = models.DateTimeField()
    changeddate = models.DateTimeField()
    mapped_devicetype = models.ForeignKey(to=DeviceType, null=True, on_delete=models.SET_NULL)
    mapped_device = models.OneToOneField(to=Device, null=True, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return '/'
    
    def __str__(self):
        return f"{self.hostname}"
    
    @property
    def slurpit_device_type(self):
        # Returns the 'slurpit_devicetype' value from the mapped_device's custom_field_data or None if not present.
        return self.mapped_device.custom_field_data.get('slurpit_devicetype')

    def copy_staged_values(self, device: SlurpitStagedDevice):
        self.slurpit_id = device.slurpit_id
        self.disabled = device.disabled
        self.hostname = device.hostname
        self.ipv4 = device.ipv4
        self.fqdn = device.fqdn
        self.device_os = device.device_os
        self.device_type = device.device_type
        self.brand = device.brand
        self.createddate = device.createddate
        self.changeddate = device.changeddate

    
