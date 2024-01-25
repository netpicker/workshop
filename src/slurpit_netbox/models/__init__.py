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

    location_name = get_config('Location')['name']
    location_defs = {'site': site}
    location, _= Location.objects.get_or_create(name=location_name, **location_defs)

    region_name = get_config('Region')['name']
    region, _= Region.objects.get_or_create(name=region_name)

    sitegroup_name = get_config('SiteGroup')['name']
    sitegroup, _= SiteGroup.objects.get_or_create(name=sitegroup_name)

    configtemplate_name = get_config('ConfigTemplate')['name']
    configtemplate, _= ConfigTemplate.objects.get_or_create(name=configtemplate_name)

    

    rack_name = get_config('Rack')['name']
    rack, _= Rack.objects.create(name=rack_name, site=site, location=location)
    

def post_migration(sender, **kwargs):
    try:
        tags = ensure_slurpit_tags()
        add_default_mandatory_objects(tags)
    except:
        pass
