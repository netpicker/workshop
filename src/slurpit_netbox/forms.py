from core.choices import DataSourceStatusChoices
from django import forms
from dcim.choices import DeviceStatusChoices, DeviceAirflowChoices
from dcim.models import DeviceRole, DeviceType, Site, Location, Region, Rack
from django.utils.translation import gettext_lazy as _
from netbox.api.fields import ChoiceField
from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms import add_blank_choice
from utilities.forms.fields import CommentField, DynamicModelChoiceField
from utilities.forms.widgets import APISelect
from tenancy.models import TenantGroup, Tenant
from utilities.forms import BootstrapMixin
from .models import ImportedDevice, Source, SlurpitPlan


class OnboardingForm(NetBoxModelBulkEditForm):
    model = ImportedDevice
    device_type = DynamicModelChoiceField(
        label=_('Device type'),
        queryset=DeviceType.objects.all(),
        required=True,
        query_params={
            'manufacturer_id': '$manufacturer'
        }
    )
    role = DynamicModelChoiceField(
        label=_('Device role'),
        queryset=DeviceRole.objects.all(),
        required=True
    )
    site = DynamicModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        required=True
    )
    region = DynamicModelChoiceField(
        label=_('Region'),
        queryset=Region.objects.all(),
        required=False
    )
    location = DynamicModelChoiceField(
        label=_('Location'),
        queryset=Location.objects.all(),
        required=False,
        query_params={
            'site_id': '$site'
        },
        initial_params={
            'racks': '$rack'
        }
    )
    rack = DynamicModelChoiceField(
        label=_('Rack'),
        queryset=Rack.objects.all(),
        required=False,
        query_params={
            'site_id': '$site',
            'location_id': '$location',
        }
    )
    position = forms.DecimalField(
        label=_('Position'),
        required=False,
        help_text=_("The lowest-numbered unit occupied by the device"),
        localize=True,
        widget=APISelect(
            api_url='/api/dcim/racks/{{rack}}/elevation/',
            attrs={
                'disabled-indicator': 'device',
                'data-dynamic-params': '[{"fieldName":"face","queryParam":"face"}]'
            },
        )
    )
    latitude = forms.DecimalField(
        label=_('Latitude'),
        max_digits=8,
        decimal_places=6,
        required=False,
        help_text=_("GPS coordinate in decimal format (xx.yyyyyy)")
    )
    longitude = forms.DecimalField(
        label=_('longitude'),
        max_digits=9,
        decimal_places=6,
        required=False,
        help_text=_("GPS coordinate in decimal format (xx.yyyyyy)")
    )
    tenant_group = DynamicModelChoiceField(
        label=_('Tenant group'),
        queryset=TenantGroup.objects.all(),
        required=False,
        null_option='None',
        initial_params={
            'tenants': '$tenant'
        }
    )
    tenant = DynamicModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False,
        query_params={
            'group_id': '$tenant_group'
        }
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False
    )
    airflow = forms.ChoiceField(
        label=_('Airflow'),
        choices=add_blank_choice(DeviceAirflowChoices),
        required=False
    )

    # platform = DynamicModelChoiceField(
    #     label=_('Platform'),
    #     queryset=Platform.objects.all(),
    #     required=False
    # )
    status = ChoiceField(
        label=_('Status'),
        choices=add_blank_choice(DeviceStatusChoices),
        required=False
    )
    
    # serial = forms.CharField(
    #     max_length=50,
    #     required=False,
    #     label=_('Serial Number')
    # )
    
    # config_template = DynamicModelChoiceField(
    #     label=_('Config template'),
    #     queryset=ConfigTemplate.objects.all(),
    #     required=False
    # )
    # comments = CommentField()
    #
    # fieldsets = (
    #     (_('Device'), ('role', 'status', 'tenant', 'platform', 'description')),
    #     (_('Location'), ('site', 'location')),
    #     (_('Hardware'), ('manufacturer', 'device_type', 'airflow', 'serial')),
    #     (_('Configuration'), ('config_template',)),
    # )
    # nullable_fields = (
    #     'location', 'tenant', 'platform', 'serial', 'airflow', 'description', 'comments',
    # )


class SourceForm(NetBoxModelForm):
    comments = CommentField()
    auth = forms.CharField(
        required=True,
        label=_("API Token"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text=_("API Token."),
    )
    verify = forms.BooleanField(
        required=False,
        initial=True,
        help_text=_(
            "Certificate validation. Uncheck if using self signed certificate."
        ),
    )

    class Meta:
        model = Source
        fields = [
            "name",
            "url",
            "auth",
            "verify",
            "description",
            "comments",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            for name, form_field in self.instance.parameters.items():
                self.fields[name].initial = self.instance.parameters.get(name)

    def save(self, *args, **kwargs):
        parameters = {}
        for name in self.fields:
            if name.startswith("auth"):
                parameters["auth"] = self.cleaned_data[name]
            if name.startswith("verify"):
                parameters["verify"] = self.cleaned_data[name]

        self.instance.parameters = parameters
        self.instance.status = DataSourceStatusChoices.NEW

        return super().save(*args, **kwargs)


class SourceFilterForm(NetBoxModelFilterSetForm):
    model = Source
    fieldsets = (
        (None, ("q", "filter_id")),
        ("Data Source", ("status",)),
    )
    status = forms.MultipleChoiceField(choices=DataSourceStatusChoices, required=False)


class SlurpitPlanTableForm(BootstrapMixin, forms.Form):
    id = DynamicModelChoiceField(
        queryset=SlurpitPlan.objects.all(),
        required=True,
        label=_("Slurpit Plans"),
    )
    # enable_cache = forms.BooleanField(
    #     label=_("Cache"),
    #     required=False,
    #     initial=True,
    #     help_text=_("Cache results for 8 hours"),
    # )