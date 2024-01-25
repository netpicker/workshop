from django.db import models
from django.utils.translation import gettext as _
from netbox.models import PrimaryModel
from ..management.choices  import SlurpitApplianceTypeChoices


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
        