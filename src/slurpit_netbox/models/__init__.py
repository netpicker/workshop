from dcim.models import DeviceRole, DeviceType, Manufacturer, Site
from django.contrib.contenttypes.models import ContentType
from extras.choices import CustomFieldTypeChoices
from extras.models import CustomField, CustomFieldChoiceSet
from extras.models.tags import Tag
from netmiko.ssh_dispatcher import CLASS_MAPPER_BASE

from .. import get_config
from .device import ImportedDevice, StagedDevice, fmt_digest
from .planning import Planning
from .setting import Source, Setting
from .logs import SlurpitLog

__all__ = [
    'ImportedDevice', 'Planning', 'Source', 'StagedDevice',
    'post_migration', 'fmt_digest', 'SlurpitLog', 'Setting'
]


netmiko_choices = get_config('netmiko_choices')
netmiko_handler = get_config('netmiko_handler')
netmiko_types = [[t, t] for t in CLASS_MAPPER_BASE]

oem_name = 'OEM'


def ensure_slurpit_tags(*items):
    if (tags := getattr(ensure_slurpit_tags, 'cache', None)) is None:
        name = 'slurpit'
        defaults = dict(slug=name, description='SlurpIT onboarded', color='F09640')
        tag, _ = Tag.objects.get_or_create(defaults, name=name)

        applicable_to = 'device', 'devicerole', 'devicetype', 'manufacturer', 'site'
        tagged_types = ContentType.objects.filter(app_label='dcim',
                                                  model__in=applicable_to)
        tag.object_types.set(tagged_types.all())
        tags = {tag}
        ensure_slurpit_tags.cache = tags
    for item in items:
        item.tags.set(tags)
    return tags


def add_netmiko_device_type_support(tags):
   
    device = ContentType.objects.get(app_label='dcim', model='device')
    

    # hostname custom field
    default_choices = {
        'description': 'hostname handlers',
        'order_alphabetically': True,
        'extra_choices': netmiko_types,
    }
    choice, _new = CustomFieldChoiceSet.objects.get_or_create(
                        defaults=default_choices,
                        name='slurpit_hostname_choice')

    slurpit_hostname_custom_field = {
        'type': CustomFieldTypeChoices.TYPE_SELECT,
        'description': "",
        'choice_set': choice,
        'is_cloneable': True,
        'label': 'Slurpit Hostname',
    }
    cf, _ = CustomField.objects.get_or_create(
                defaults=slurpit_hostname_custom_field,
                name='slurpit_hostname')
    cf.content_types.set({device})


    # fqdn custome field
    default_choices = {
        'description': 'fqdn handlers',
        'order_alphabetically': True,
        'extra_choices': netmiko_types,
    }
    choice, _new = CustomFieldChoiceSet.objects.get_or_create(
                        defaults=default_choices,
                        name='slurpit_fqdn_choice')
    
    slurpit_fqdn_custom_field = {
        'type': CustomFieldTypeChoices.TYPE_SELECT,
        'choice_set': choice,
        'description': "",
        'label': 'Slurpit Fqdn',
        'is_cloneable': True,
    }
    cf, _ = CustomField.objects.get_or_create(
                defaults=slurpit_fqdn_custom_field,
                name='slurpit_fqdn')
    cf.content_types.set({device})
    
    # platform custom field
    default_choices = {
        'description': 'platform handlers',
        'order_alphabetically': True,
        'extra_choices': netmiko_types,
    }
    choice, _new = CustomFieldChoiceSet.objects.get_or_create(
                        defaults=default_choices,
                        name='slurpit_platform_choice')
    
    slurpit_platform_custom_field = {
        'type': CustomFieldTypeChoices.TYPE_SELECT,
        'description': "",
        'choice_set': choice,
        'is_cloneable': True,
        'label': 'Slurpit Platform',
    }
    cf, _ = CustomField.objects.get_or_create(
                defaults=slurpit_platform_custom_field,
                name='slurpit_platform')
    cf.content_types.set({device})

    # manufactor custom field
    default_choices = {
        'description': 'fqdn handlers',
        'order_alphabetically': True,
        'extra_choices': netmiko_types,
    }
    choice, _new = CustomFieldChoiceSet.objects.get_or_create(
                        defaults=default_choices,
                        name='slurpit_manufactor_choice')
    slurpit_manufactor_custom_field = {
        'type': CustomFieldTypeChoices.TYPE_SELECT,
        'description': "",
        'choice_set': choice,
        'is_cloneable': True,
        'label': 'Slurpit Manufactor',
    }
    cf, _ = CustomField.objects.get_or_create(
                defaults=slurpit_manufactor_custom_field,
                name='slurpit_manufactor')
    cf.content_types.set({device})

    # device type custom field
    default_choices = {
        'description': 'device type handlers',
        'order_alphabetically': True,
        'extra_choices': netmiko_types,
    }
    choice, _new = CustomFieldChoiceSet.objects.get_or_create(
                        defaults=default_choices,
                        name='slurpit_device_type_choice')
    
    slurpit_devicetype_custom_field = {
        'type': CustomFieldTypeChoices.TYPE_SELECT,
        'description': "",
        'choice_set': choice,
        'is_cloneable': True,
        'label': 'Slurpit Device Type',
    }
    cf, _ = CustomField.objects.get_or_create(
                defaults=slurpit_devicetype_custom_field,
                name='slurpit_devicetype')
    cf.content_types.set({device})


def add_default_mandatory_objects(tags):
    site_name = get_config('Site')['name']
    site_defs = {'slug': site_name.lower()}
    site, _ = Site.objects.get_or_create(defaults=site_defs, name=site_name)
    site.tags.set(tags)

    manu_defs = {'slug': oem_name.lower()}
    manu, _ = Manufacturer.objects.get_or_create(defaults=manu_defs, name=oem_name)
    manu.tags.set(tags)

    devtype_model = get_config('DeviceType')['model']
    type_defs = {'manufacturer': manu}
    dtype, _ = DeviceType.objects.get_or_create(model=devtype_model, **type_defs)
    dtype.tags.set(tags)

    role_name = get_config('DeviceRole')['name']
    role_defs = {}
    role, _ = DeviceRole.objects.get_or_create(defaults=role_defs, name=role_name)
    role.tags.set(tags)


def post_migration(sender, **kwargs):
    try:
        from .planning import Planning
        from ..views.planning import make_planning_tabs
        tags = ensure_slurpit_tags()
        add_netmiko_device_type_support(tags)
        add_default_mandatory_objects(tags)
        planning = Planning.get_planning()
        make_planning_tabs(planning)
    except:
        pass
