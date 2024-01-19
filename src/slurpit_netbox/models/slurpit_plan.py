from django.db import models
from netbox.models import PrimaryModel
from django.urls import reverse

class SlurpitPlan(PrimaryModel):
    name = models.TextField(max_length=255, null=True)
    plan_id = models.TextField(max_length=10, unique=True)
    selected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}"
    
    def get_absolute_url(self):
        return reverse("plugins:slurpit_netbox:slurpitplan", args=[self.pk])
    

