from dcim.models import DeviceRole, DeviceType, Manufacturer, Site, Location, Region, SiteGroup, Rack
from django.contrib.contenttypes.models import ContentType
from extras.choices import CustomFieldTypeChoices
from extras.models import CustomField, CustomFieldChoiceSet, ConfigTemplate
from extras.models.tags import Tag

from .. import get_config
from .device import SlurpitImportedDevice, SlurpitStagedDevice
from .planning import SlurpitPlanning, SlurpitSnapshot
from .setting import SlurpitSetting
from .logs import SlurpitLog

__all__ = [
    'SlurpitImportedDevice', 'SlurpitStagedDevice',
    'post_migration', 'SlurpitLog', 'SlurpitSetting'
]

def ensure_slurpit_tags(*items):
    if (tags := getattr(ensure_slurpit_tags, 'cache', None)) is None:
        name = 'slurpit'
        defaults = dict(slug=name, description='Slurp\'it onboarded', color='F09640')
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

def create_custom_fields():   
    device = ContentType.objects.get(app_label='dcim', model='device')
    

    # hostname custom field
    default_choices = {
        'description': 'hostname handlers',
        'order_alphabetically': True,
        'extra_choices':{},
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
        'extra_choices':{},
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
        'extra_choices':{},
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
        'extra_choices':{},
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
        'extra_choices':{},
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
    site, _ = Site.objects.get_or_create(**get_config('Site'))
    site.tags.set(tags)

    manu, _ = Manufacturer.objects.get_or_create(**get_config('Manufacturer'))
    manu.tags.set(tags)

    dtype, _ = DeviceType.objects.get_or_create(manufacturer=manu, **get_config('DeviceType'))
    dtype.tags.set(tags)

    role, _ = DeviceRole.objects.get_or_create(**get_config('DeviceRole'))
    role.tags.set(tags)

    location, _= Location.objects.get_or_create(site=site, **get_config('Location'))

    region, _= Region.objects.get_or_create(**get_config('Region'))

    sitegroup, _= SiteGroup.objects.get_or_create(**get_config('SiteGroup'))

    configtemplate, _= ConfigTemplate.objects.get_or_create(**get_config('ConfigTemplate'))

    rack, _= Rack.objects.get_or_create(site=site, location=location, **get_config('Rack'))
    

def post_migration(sender, **kwargs):
    create_custom_fields()
    tags = ensure_slurpit_tags()
    add_default_mandatory_objects(tags)
