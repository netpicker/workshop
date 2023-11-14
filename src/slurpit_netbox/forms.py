from dcim.choices import DeviceStatusChoices
from dcim.models import DeviceRole, DeviceType, Site
from django.utils.translation import gettext_lazy as _
from netbox.api.fields import ChoiceField
from netbox.forms import NetBoxModelBulkEditForm
from utilities.forms import add_blank_choice
from utilities.forms.fields import DynamicModelChoiceField

from .models import ImportedDevice


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
