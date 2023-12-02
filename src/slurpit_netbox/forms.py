from core.choices import DataSourceStatusChoices
from django import forms
from dcim.choices import DeviceStatusChoices
from dcim.models import DeviceRole, DeviceType, Site
from django.utils.translation import gettext_lazy as _
from netbox.api.fields import ChoiceField
from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms import add_blank_choice
from utilities.forms.fields import CommentField, DynamicModelChoiceField

from .models import ImportedDevice, Source


class OnboardingForm(NetBoxModelBulkEditForm):
    model = ImportedDevice
    device_type = DynamicModelChoiceField(
        label=_('Device type'),
        queryset=DeviceType.objects.all(),
        required=False,
        query_params={
            'manufacturer_id': '$manufacturer'
        }
    )
    role = DynamicModelChoiceField(
        label=_('Device role'),
        queryset=DeviceRole.objects.all(),
        required=False
    )
    site = DynamicModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        required=False
    )
    # location = DynamicModelChoiceField(
    #     label=_('Location'),
    #     queryset=Location.objects.all(),
    #     required=False,
    #     query_params={
    #         'site_id': '$site'
    #     }
    # )
    # tenant = DynamicModelChoiceField(
    #     label=_('Tenant'),
    #     queryset=Tenant.objects.all(),
    #     required=False
    # )
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
    # airflow = forms.ChoiceField(
    #     label=_('Airflow'),
    #     choices=add_blank_choice(DeviceAirflowChoices),
    #     required=False
    # )
    # serial = forms.CharField(
    #     max_length=50,
    #     required=False,
    #     label=_('Serial Number')
    # )
    # description = forms.CharField(
    #     label=_('Description'),
    #     max_length=200,
    #     required=False
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
        help_text=_("IP Fabric API Token."),
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
