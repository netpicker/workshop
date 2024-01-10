from django.db import models
from netbox.models import NetBoxModel


class PlanningDataTab(NetBoxModel):
    index = models.TextField(max_length=20, unique=True)
    name = models.TextField(max_length=255, null=True)
    flags = models.TextField(max_length=10, null=True)
    type = models.TextField(max_length=50, null=True)
    act_mtu = models.TextField(max_length=50, null=True)
    l2_mtu = models.TextField(max_length=50, null=True)
    max_mtu = models.TextField(max_length=50, null=True)
    mac_addr = models.TextField(max_length=50, null=True)
    timestamp = models.DateTimeField(null=True)
   
    def __str__(self):
        return f"{self.name}"