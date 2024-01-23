import logging
from core.choices import DataSourceStatusChoices
from core.models import Job
from django.db import models
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from netbox.models import PrimaryModel
from slurpit_netbox.slurpitch import SlurpitSession
from ..management.choices  import SlurpitApplianceTypeChoices

def apply_tags(object, tags):
    def _apply(object):
        for tag in tags:
            if hasattr(object, "tags"):
                object.tags.add(tag)
        object.save()
    _apply(object)


class SlurpitSource(PrimaryModel):
    name = models.CharField(max_length=100, unique=True)
    url = models.CharField(max_length=200, verbose_name=_("URL"))
    status = models.CharField(
        max_length=50,
        choices=DataSourceStatusChoices,
        default=DataSourceStatusChoices.NEW,
        editable=False,
    )
    parameters = models.JSONField(blank=True, null=True)
    last_synced = models.DateTimeField(blank=True, null=True, editable=False)

    class Meta:
        ordering = ("name",)
        verbose_name = "Data source"
        verbose_name_plural = "Data sources"

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse("plugins:slurpit_netbox:source", args=[self.pk])

    def get_session(self):
        ssl_verify = self.parameters.get('verify', True)
        token = self.parameters.get('auth')
        return SlurpitSession(self.url, token, ssl_verify)

    @property
    def ready_for_sync(self):
        return self.status not in (
            DataSourceStatusChoices.QUEUED,
            DataSourceStatusChoices.SYNCING,
        )

    @property
    def docs_url(self):
        # TODO: Add docs url
        return ""

    def clean(self):
        super().clean()

        self.url = self.url.rstrip("/")

class SlurpitSetting(PrimaryModel):
    server_url = models.CharField(max_length=200, verbose_name=_("URL"))
    api_key = models.CharField(max_length=50,editable=False)
    last_synced = models.DateTimeField(blank=True, auto_now=True,null=True, editable=False)
    connection_status = models.CharField(max_length=50,editable=False, null=True, default='')
    push_api_key = models.CharField(max_length=200,null=True, editable=False)
    
    appliance_type = models.CharField(
        verbose_name=_('Applicance Type'),
        max_length=50,
        choices=SlurpitApplianceTypeChoices,
        blank=True
    )

    class Meta:
        verbose_name = "setting"
        verbose_name_plural = "setting"

    def __str__(self):
        return f"{self.server_url}"

    def get_absolute_url(self):
        return '/'

    @property
    def docs_url(self):
        # TODO: Add docs url
        return ""

    def clean(self):
        super().clean()
        