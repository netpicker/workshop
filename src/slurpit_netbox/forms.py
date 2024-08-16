from core.choices import DataSourceStatusChoices
from django import forms
from dcim.choices import DeviceStatusChoices, DeviceAirflowChoices, DeviceStatusChoices, InterfaceSpeedChoices
from dcim.models import DeviceRole, DeviceType, Site, Location, Region, Rack, Device, Interface, Module
from django.utils.translation import gettext_lazy as _
from netbox.api.fields import ChoiceField
from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms import add_blank_choice
from utilities.forms.fields import CommentField, DynamicModelChoiceField, DynamicModelMultipleChoiceField
from utilities.forms.widgets import APISelect, NumberWithOptions, HTMXSelect
from tenancy.models import TenantGroup, Tenant
from tenancy.forms import TenancyForm
from .models import SlurpitImportedDevice, SlurpitPlanning, SlurpitSetting, SlurpitInitIPAddress, SlurpitInterface, SlurpitPrefix, SlurpitVLAN
from .management.choices import SlurpitApplianceTypeChoices
from extras.models import CustomField
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from virtualization.models import VMInterface
from ipam.models import FHRPGroup, VRF, IPAddress, VLANGroup, VLAN, Role
from ipam.choices import *
from ipam.constants import *
from dcim.forms.common import InterfaceCommonForm
from ipam.forms import PrefixForm
from utilities.forms import form_from_model

class DeviceComponentForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        selector=True,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Disable reassignment of Device when editing an existing instance
        if self.instance.pk:
            self.fields['device'].disabled = False

class ModularDeviceComponentForm(DeviceComponentForm):
    module = DynamicModelChoiceField(
        label=_('Module'),
        queryset=Module.objects.all(),
        required=False,
        query_params={
            'device_id': '$device',
        }
    )



class OnboardingForm(NetBoxModelBulkEditForm):
    model = SlurpitImportedDevice
    interface_name = forms.CharField(
        label=_('Management Interface'),
        initial='Management1',
        max_length=200,
        required=True
    )
    
    device_type = forms.ChoiceField(
        choices=[],
        label=_('Device type'),
        required=True
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
    status = ChoiceField(
        label=_('Status'),
        choices=add_blank_choice(DeviceStatusChoices),
        required=False
    )
    def __init__(self, *args, **kwargs):
        device_types = kwargs['initial'].pop('device_types', None)
        super().__init__(*args, **kwargs)
        choices = []
        if device_types and len(device_types) > 1:
            choices = [('keep_original', 'Keep Original Type')]
        for dt in DeviceType.objects.all().order_by('id'):
            choices.append((dt.id, dt.model))          
        self.fields['device_type'].choices = choices

class SlurpitPlanningTableForm(forms.Form):
    planning_id = DynamicModelChoiceField(
        queryset=SlurpitPlanning.objects.all(),
        to_field_name='planning_id',
        required=True,
        label=_("Slurpit Plans"),
    )

class SlurpitApplianceTypeForm(forms.Form):
    model =  SlurpitSetting
    appliance_type = forms.ChoiceField(
        label=_('Data synchronization'),
        choices=add_blank_choice(SlurpitApplianceTypeChoices),
        required=False
    )

class SlurpitMappingForm(forms.Form):
    source_field = forms.CharField(
        required=True,
        label=_("Source Field"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text=_("Slurpit Device's Field"),
    )
    
    target_field = forms.ChoiceField(
        choices=[
        ],
        required=True,
        label=f"Target Field",
    )
    
    
    def __init__(self, *args, **kwargs):
        choice_name = kwargs.pop('choice_name', None) 
        doaction = kwargs.pop('doaction', None) 
        super(SlurpitMappingForm, self).__init__(*args, **kwargs)
        
        choices = []
        
        for field in Device._meta.get_fields():
            if not field.is_relation or field.one_to_one or (field.many_to_one and field.related_model):
                choices.append((f'device|{field.name}', f'device | {field.name}'))
        
        # Add custom fields
        device = ContentType.objects.get(app_label='dcim', model='device')
        device_custom_fields = CustomField.objects.filter(object_types=device)

        for custom_field in device_custom_fields:
            choices.append((f'device|cf_{custom_field.name}', f'device | {custom_field.name}'))
        
        self.fields[f'target_field'].choices = choices

        if doaction != "add":
            self.fields[f'target_field'].label = choice_name
            del self.fields[f'source_field']


class SlurpitDeviceForm(forms.Form):
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=True,
        label=_("Device"),
    )

class SlurpitDeviceStatusForm(forms.Form):
    device_status = forms.ChoiceField(
        label=_('Status'),
        choices=add_blank_choice(DeviceStatusChoices),
        required=False
    )

class SlurpitInitIPAMForm(TenancyForm, NetBoxModelForm):
    vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label=_('VRF')
    )
    enable_reconcile = forms.BooleanField(
        required=False,
        label=_('Enable to reconcile every incoming IPAM data')
    )
    ignore_status = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_role = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data'),
    )
    ignore_vrf = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data'),
    )
    ignore_tenant = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data'),
    )
    ignore_description = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data'),
    )

    comments = CommentField()

    class Meta:
        model = SlurpitInitIPAddress
        fields = [
            'vrf', 'status', 'ignore_status', 'role', 'tenant_group',
            'tenant','description', 'enable_reconcile','ignore_role', 'ignore_tenant', 'ignore_description'
        ]

    def __init__(self, *args, **kwargs):
        # Initialize helper selectors
        initial = kwargs.get('initial', {}).copy()
        kwargs['initial'] = initial

        super().__init__(*args, **kwargs)
        del self.fields['tags']
    
class SlurpitInitIPAMEditForm(SlurpitInitIPAMForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['enable_reconcile']

class SlurpitDeviceInterfaceForm(InterfaceCommonForm, ModularDeviceComponentForm):
    enable_reconcile = forms.BooleanField(
        required=False,
        label=_('Enable to reconcile every incoming Device Interface data')
    )
    
    vlan_group = DynamicModelChoiceField(
        queryset=VLANGroup.objects.all(),
        required=False,
        label=_('VLAN group')
    )

    untagged_vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label=_('Untagged VLAN'),
        query_params={
            'group_id': '$vlan_group',
            'available_on_device': '$device',
        }
    )

    tagged_vlans = DynamicModelMultipleChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label=_('Tagged VLANs'),
        query_params={
            'group_id': '$vlan_group',
            'available_on_device': '$device',
        }
    )

    ignore_module = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_type = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_speed = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_duplex = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )

    class Meta:
        model = SlurpitInterface
        fields = [
           'module', 'name', 'label', 'type', 'speed', 'duplex',  'description', 'mode', 'vlan_group', 'untagged_vlan', 'tagged_vlans', 'enable_reconcile',
            'ignore_module', 'ignore_type', 'ignore_speed', 'ignore_duplex'
        ]
        widgets = {
            'speed': NumberWithOptions(
                options=InterfaceSpeedChoices
            ),
            'mode': HTMXSelect(),
        }
        labels = {
            'mode': '802.1Q Mode',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['tags']
        del self.fields['device']

class SlurpitDeviceInterfaceEditForm(SlurpitDeviceInterfaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['enable_reconcile']

class SlurpitPrefixForm(PrefixForm):
    enable_reconcile = forms.BooleanField(
        required=False,
        label=_('Enable to reconcile every incoming Prefix data')
    )
    ignore_status = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_vrf = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_role = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_site = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_vlan = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_tenant = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_description = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    
    class Meta:
        model = SlurpitPrefix
        fields = [
            'prefix', 'vrf', 'site', 'vlan', 'status', 'role', 'is_pool', 'mark_utilized', 'tenant_group', 'tenant',
            'description', 'comments', 'tags','enable_reconcile', 'ignore_status', 'ignore_vrf', 'ignore_role', 'ignore_site', 'ignore_vlan',
            'ignore_tenant', 'ignore_description'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['tags']
class ComponentBulkEditForm(NetBoxModelBulkEditForm):
    device = forms.ModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        disabled=True,
        widget=forms.HiddenInput()
    )
    module = forms.ModelChoiceField(
        label=_('Module'),
        queryset=Module.objects.all(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit module queryset to Modules which belong to the parent Device
        if 'device' in self.initial:
            device = Device.objects.filter(pk=self.initial['device']).first()
            self.fields['module'].queryset = Module.objects.filter(device=device)
        else:
            self.fields['module'].choices = ()
            self.fields['module'].widget.attrs['disabled'] = True

class SlurpitInterfaceBulkEditForm(
    form_from_model(SlurpitInterface, [
        'label',  'type', 'speed', 'duplex',  'description', 'mode'
    ]),
    ComponentBulkEditForm
):
    # enable_reconcile = forms.BooleanField(
    #     required=False,
    #     label=_('Enable to reconcile every incoming Device Interface data')
    # )
    
    model = SlurpitInterface

    nullable_fields = (
        'module', 'label', 'parent', 'bridge', 'lag', 'speed', 'duplex', 'mac_address', 'wwn', 'vdcs', 'mtu',
        'description', 'poe_mode', 'poe_type', 'mode', 'rf_channel', 'rf_channel_frequency', 'rf_channel_width',
        'tx_power', 'untagged_vlan', 'tagged_vlans', 'vrf', 'wireless_lans'
    )

    fields = [
        'module', 'name', 'label', 'type', 'speed', 'duplex',  'description', 'mode',
    ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['add_tags']
        del self.fields['remove_tags']

class SlurpitPrefixBulkEditForm(
    form_from_model(SlurpitPrefix, [
        'vrf', 'site', 'status', 'role','tenant', 'description', 'comments'
    ]),
    NetBoxModelBulkEditForm
):
    # enable_reconcile = forms.BooleanField(
    #     required=False,
    #     label=_('Enable to reconcile every incoming Prefix data')
    # )

    nullable_fields = (
        'site', 'vrf', 'tenant', 'role', 'description', 'comments',
    )
    tenant = DynamicModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False
    )
    role = DynamicModelChoiceField(
        label=_('Role'),
        queryset=Role.objects.all(),
        required=False
    )
    vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label=_('VRF')
    )
    model = SlurpitPrefix
    fields = [
       'vrf', 'site', 'vlan', 'status', 'role', 'is_pool', 'mark_utilized', 'tenant_group', 'tenant',
        'description', 'comments', 'tags'
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['add_tags']
        del self.fields['remove_tags']
class SlurpitIPAddressBulkEditForm(
    form_from_model(SlurpitInitIPAddress, [
        'vrf', 'status', 'role', 'tenant', 'description'
    ]),
    NetBoxModelBulkEditForm
):
    tenant = DynamicModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False
    )
    vrf = DynamicModelChoiceField(
        queryset=VRF.objects.all(),
        required=False,
        label=_('VRF')
    )
    nullable_fields = (
        'vrf', 'role', 'tenant', 'dns_name', 'description', 'comments',
    )
    model = SlurpitInitIPAddress
    fields = [
        'vrf', 'status', 'role', 'tenant_group',
        'tenant','description'
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        del self.fields['add_tags']
        del self.fields['remove_tags']

class SlurpitVLANForm(TenancyForm, NetBoxModelForm):
    site = DynamicModelChoiceField(
        label=_('Site'),
        queryset=Site.objects.all(),
        required=False,
        null_option='None',
        selector=True
    )
    role = DynamicModelChoiceField(
        label=_('Role'),
        queryset=Role.objects.all(),
        required=False
    )

    enable_reconcile = forms.BooleanField(
        required=False,
        label=_('Enable to reconcile every incoming Prefix data')
    )

    ignore_status = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_site = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_group = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_vid = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_role = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_tenant = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    ignore_description = forms.BooleanField(
        required=False,
        label=_('Ignore value for updating data')
    )
    class Meta:
        model = SlurpitVLAN
        fields = [
            'enable_reconcile', 
            'site', 
            'group', 
            'vid', 
            'name', 
            'status', 
            'role', 
            'tenant_group', 
            'tenant', 
            'description',
            'ignore_status',
            'ignore_site',
            'ignore_group',
            'ignore_vid',
            'ignore_role',
            'ignore_tenant',
            'ignore_description'
        ]

class SlurpitVLANEditForm(SlurpitVLANForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['enable_reconcile']

class SlurpitVLANBulkEditForm(
    form_from_model(SlurpitVLAN, [
        'status', 'role', 'tenant', 'description'
    ]),
    NetBoxModelBulkEditForm
):
    tenant = DynamicModelChoiceField(
        label=_('Tenant'),
        queryset=Tenant.objects.all(),
        required=False
    )
    role = DynamicModelChoiceField(
        label=_('Role'),
        queryset=Role.objects.all(),
        required=False
    )
    nullable_fields = (
        'role', 'tenant','description',
    )
    model = SlurpitVLAN
    fields = [
        'status', 'role', 'role', 'tenant_group',
        'tenant','description'
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        del self.fields['add_tags']
        del self.fields['remove_tags']