from django.db import models
from netbox.models import NetBoxModel

class SlurpitMapping(NetBoxModel):
    source_field = models.CharField(max_length=255, unique=True)
    target_field = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.source_field}"