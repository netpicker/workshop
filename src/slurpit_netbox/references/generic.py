from . import base_name, plugin_type
from .imports import *

from .. import get_config
from ..models import  SlurpitStagedDevice, ensure_slurpit_tags

from django.utils.text import slugify

def create_form(form, data, model, initial):
    return form(data, initial=initial)

def get_form_device_data(form):
    return {
            'role': form.cleaned_data['role'],
            'site': form.cleaned_data['site'],
            'location': form.cleaned_data['location'],
            'rack': form.cleaned_data['rack'],
            'position': form.cleaned_data['position'],
            'latitude': form.cleaned_data['latitude'],
            'longitude': form.cleaned_data['longitude'],
            'tenant': form.cleaned_data['tenant'],
            'description': form.cleaned_data['description'],
            'airflow': form.cleaned_data['airflow'],
        }

def set_device_custom_fields(device, fields):
    for k, v in fields.items():
        device.custom_field_data[k] = v

def get_default_objects():
    return {
        'device_type': DeviceType.objects.get(**get_config('DeviceType')),
        'role': DeviceRole.objects.get(**get_config('DeviceRole')),
        'site': Site.objects.get(**get_config('Site')),
    }

def status_inventory():
    return DeviceStatusChoices.STATUS_INVENTORY

def status_offline():
    return DeviceStatusChoices.STATUS_OFFLINE

def get_create_dcim_objects(staged: SlurpitStagedDevice):
    manu, new = Manufacturer.objects.get_or_create(name=staged.brand, defaults={'slug':slugify(staged.brand)})
    if new:
        ensure_slurpit_tags(manu)
    platform, new = Platform.objects.get_or_create(name=staged.device_os, defaults={'slug':slugify(staged.device_os)})
    dtype, new = DeviceType.objects.get_or_create(model=staged.device_type, manufacturer=manu, defaults={'slug':slugify(f'{staged.brand}-{staged.device_type}'), 'default_platform':platform})
    if new:
        ensure_slurpit_tags(dtype)
    return dtype

class SlurpitViewMixim:
    slurpit_data = {
            'plugin_type': plugin_type,
            'base_name': base_name,
            'plugin_base_name': f"plugins:{base_name}",
            'version': get_config('version'),
    }
    
    def get_extra_context(self, request):
        return {**self.slurpit_data, **self.slurpit_extra_context()}
    
    def slurpit_extra_context(self):
        return {}

class SlurpitViewSet(NetBoxModelViewSet):
    pass

class SlurpitQuerySetMixim:
    pass