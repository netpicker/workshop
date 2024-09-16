from dcim.models import DeviceRole, DeviceType, Manufacturer, Site, Location, Region, SiteGroup, Rack
from extras.choices import CustomFieldTypeChoices
from extras.models import CustomField, CustomFieldChoiceSet, ConfigTemplate
from extras.models.tags import Tag
from core.models import ObjectType
from django.db.models import Q, Transform, CharField, TextField

from .. import get_config
from .device import SlurpitImportedDevice, SlurpitStagedDevice
from .planning import SlurpitPlanning, SlurpitSnapshot
from .setting import SlurpitSetting
from .logs import SlurpitLog
from .mapping import SlurpitMapping
from .ipam import SlurpitInitIPAddress
from .interface import SlurpitInterface
from .prefix import SlurpitPrefix
from .vlan import SlurpitVLAN
__all__ = [
    'SlurpitImportedDevice', 'SlurpitStagedDevice', 'SlurpitInitIPAddress'
    'post_migration', 'SlurpitLog', 'SlurpitSetting'
]

def ensure_slurpit_tags(*items):
    if (tags := getattr(ensure_slurpit_tags, 'cache', None)) is None:
        name = 'slurpit'
        tag, _ = Tag.objects.get_or_create(name=name, defaults={'slug':name, 'description':'Slurp\'it onboarded', 'color': 'F09640'})

        dcim_applicable_to = 'device', 'devicerole', 'devicetype', 'manufacturer', 'site'
        ipam_applicable = 'iprange'
        slurpit_netbox_applicable_to = 'slurpitinitipaddress', 'slurpitinterface', 'slurpitprefix'

        dcim_Q = Q(app_label='dcim', model__in=dcim_applicable_to)
        ipam_Q = Q(app_label='ipam', model=ipam_applicable)
        slurpit_Q = Q(app_label='slurpit_netbox', model__in=slurpit_netbox_applicable_to)

        tagged_types = ObjectType.objects.filter(ipam_Q | dcim_Q | slurpit_Q)
        tag.object_types.set(tagged_types.all())
        tags = {tag}
        ensure_slurpit_tags.cache = tags
    for item in items:
        item.tags.set(tags)
    return tags

def create_custom_fields():   
    device = ObjectType.objects.get(app_label='dcim', model='device')
    cf, _ = CustomField.objects.get_or_create(
                name='slurpit_hostname',   
                defaults={            
                    "type":CustomFieldTypeChoices.TYPE_TEXT,
                    "description":"",
                    "is_cloneable":True,
                    "label":'Hostname',
                    "group_name":"Slurp'it"
                })
    cf.object_types.set({device})

    cf, _ = CustomField.objects.get_or_create(
                name='slurpit_fqdn',  
                defaults={                     
                    "type":CustomFieldTypeChoices.TYPE_TEXT,
                    "description":"",
                    "is_cloneable":True,
                    "label":'Fqdn',
                    "group_name":"Slurp'it"
                })
    cf.object_types.set({device})
        
    cf, _ = CustomField.objects.get_or_create(
                name='slurpit_platform',
                defaults={            
                    "type":CustomFieldTypeChoices.TYPE_TEXT,
                    "description":"",
                    "is_cloneable":True,
                    "label":'Platform',
                    "group_name":"Slurp'it",
                })
    cf.object_types.set({device})

    cf, _ = CustomField.objects.get_or_create(
                name='slurpit_manufacturer', 
                defaults={            
                    "type":CustomFieldTypeChoices.TYPE_TEXT,
                    "description":"",
                    "is_cloneable":True,
                    "label":'Manufacturer',
                    "group_name":"Slurp'it",
                })
    cf.object_types.set({device})
    
    cf, _ = CustomField.objects.get_or_create(
                name='slurpit_devicetype',
                defaults={            
                    "type":CustomFieldTypeChoices.TYPE_TEXT,
                    "description":"",
                    "is_cloneable":True,
                    "label":'Device Type',
                    "group_name":"Slurp'it",
                })
    cf.object_types.set({device})
    
    cf, _ = CustomField.objects.get_or_create(
                name='slurpit_ipv4',
                defaults={            
                    "type":CustomFieldTypeChoices.TYPE_TEXT,
                    "description":"",
                    "is_cloneable":True,
                    "label":'Ipv4',
                    "group_name":"Slurp'it",
                })
    cf.object_types.set({device})

def create_default_data_mapping():
    SlurpitMapping.objects.all().delete()
    
    mappings = [
        {"source_field": "hostname", "target_field": "device|name"},
        {"source_field": "fqdn", "target_field": "device|primary_ip4"},
        {"source_field": "ipv4", "target_field": "device|primary_ip4"},
        {"source_field": "device_os", "target_field": "device|platform"},
        {"source_field": "device_type", "target_field": "device|device_type"},
    ]
    for mapping in mappings:
        SlurpitMapping.objects.get_or_create(**mapping)

def add_default_mandatory_objects(tags):
    site, _ = Site.objects.get_or_create(**get_config('Site'))
    site.tags.set(tags)

    manu, _ = Manufacturer.objects.get_or_create(**get_config('Manufacturer'))
    manu.tags.set(tags)

    dtype, _ = DeviceType.objects.get_or_create(manufacturer=manu, **get_config('DeviceType'))
    dtype.tags.set(tags)

    role, _ = DeviceRole.objects.get_or_create(**get_config('DeviceRole'))
    role.tags.set(tags)    

    create_default_data_mapping()


def post_migration(sender, **kwargs):
    create_custom_fields()
    tags = ensure_slurpit_tags()
    add_default_mandatory_objects(tags)

class LowerCase(Transform):
    lookup_name = "lower"
    function = "LOWER"

CharField.register_lookup(LowerCase)
TextField.register_lookup(LowerCase)