from dcim.models import DeviceRole, DeviceType, Manufacturer, Site
from django.contrib.contenttypes.models import ContentType
from extras.choices import CustomFieldTypeChoices
from extras.models import CustomField, CustomFieldChoiceSet
from netmiko.ssh_dispatcher import CLASS_MAPPER_BASE

from .. import get_config
from .device import ImportedDevice, StagedDevice, fmt_digest

__all__ = ['ImportedDevice', 'StagedDevice', 'ensure_default_instances', 'fmt_digest']


netmiko_choices = get_config('netmiko_choices')
netmiko_handler = get_config('netmiko_handler')
netmiko_types = [[t, t] for t in CLASS_MAPPER_BASE]

oem_name = 'OEM'


def add_netmiko_device_type_support():
    default_choices = {
        'description': 'NetMiko supported handlers',
        'extra_choices': netmiko_types,
        'order_alphabetically': True,
    }
    choice, _new = CustomFieldChoiceSet.objects.get_or_create(
                        defaults=default_choices,
                        name=netmiko_choices)

    default_custom_field = {
        'type': CustomFieldTypeChoices.TYPE_SELECT,
        'choice_set': choice,
        'description': "Netmiko handler's name for integrations",
        'is_cloneable': True,
    }
    cf, _ = CustomField.objects.get_or_create(
                defaults=default_custom_field,
                name=netmiko_handler)

    device = ContentType.objects.get(app_label='dcim', model='device')
    cf.content_types.set({device})


def add_default_mandatory_objects():
    site_name = get_config('Site')['name']
    site_defs = {'slug': site_name.lower()}
    site, _ = Site.objects.get_or_create(defaults=site_defs, name=site_name)

    manu_defs = {'slug': oem_name.lower()}
    manu, _ = Manufacturer.objects.get_or_create(defaults=manu_defs, name=oem_name)

    devtype_model = get_config('DeviceType')['model']
    type_defs = {'manufacturer': manu}
    type, _ = DeviceType.objects.get_or_create(defaults=type_defs, model=devtype_model)

    role_name = get_config('DeviceRole')['name']
    role_defs = {}
    role, _ = DeviceRole.objects.get_or_create(defaults=role_defs, name=role_name)


def ensure_default_instances():
    add_netmiko_device_type_support()
    add_default_mandatory_objects()
