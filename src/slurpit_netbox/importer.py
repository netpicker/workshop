import requests

from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.db.models import QuerySet, F, OuterRef, Subquery
from django.utils import timezone
from django.db.models.expressions import RawSQL
from django.utils.text import slugify

from . import get_config
from .models import SlurpitImportedDevice, SlurpitStagedDevice, ensure_slurpit_tags, SlurpitLog, SlurpitSetting, SlurpitPlanning, SlurpitSnapshot
from .management.choices import *
from .references import base_name, plugin_type, custom_field_data_name
from .references.generic import get_default_objects, status_inventory, status_offline, get_create_dcim_objects, set_device_custom_fields
from .references.imports import *
from dcim.models import Interface
from ipam.models import IPAddress

BATCH_SIZE = 256
columns = ('slurpit_id', 'disabled', 'hostname', 'fqdn', 'ipv4', 'device_os', 'device_type', 'brand', 'createddate', 'changeddate')


def get_devices(offset):
    try:
        setting = SlurpitSetting.objects.get()
        uri_base = setting.server_url
        headers = {
                        'authorization': setting.api_key,
                        'useragent': f"{plugin_type}/requests",
                        'accept': 'application/json'
                    }
        uri_devices = f"{uri_base}/api/devices?offset={offset}&limit={BATCH_SIZE}"
        r = requests.get(uri_devices, headers=headers, timeout=15, verify=False)
        # r.raise_for_status()
        data = r.json()
        log_message = f"Syncing the devices from Slurp'it in {plugin_type.capitalize()}."
        SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=log_message)
        return data, ""
    except ObjectDoesNotExist:
        setting = None
        log_message = "Need to set the setting parameter"
        SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=log_message)
        return None, log_message
    except Exception as e:
        log_message = "Please confirm the Slurp'it server is running and reachable."
        return None, log_message

def start_device_import():
    with connection.cursor() as cursor:
        cursor.execute(f"truncate {SlurpitStagedDevice._meta.db_table} cascade")

def import_devices(devices):
    to_insert = []
    for device in devices:
        # if device.get('disabled') == '1':
        #     continue
        if device.get('device_type') is None:
            SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=f"Missing device type, cannot import device {device.get('hostname')}")
            continue
        device['slurpit_id'] = device.pop('id')
        
        try:
            device['createddate'] = timezone.make_aware(datetime.strptime(device['createddate'], '%Y-%m-%d %H:%M:%S'), timezone.get_current_timezone())
            device['changeddate'] = timezone.make_aware(datetime.strptime(device['changeddate'], '%Y-%m-%d %H:%M:%S'), timezone.get_current_timezone())          
        except ValueError:
            SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=f"Failed to convert to datetime, cannot import {device.get('hostname')}")
            continue
        to_insert.append(SlurpitStagedDevice(**{key: value for key, value in device.items() if key in columns}))
    SlurpitStagedDevice.objects.bulk_create(to_insert)
    SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=f"Sync staged {len(to_insert)} devices")


def process_import(delete=True):
    if delete:
        handle_parted()
    handle_changed()
    handle_new_comers()
    
    SlurpitLog.success(category=LogCategoryChoices.ONBOARD, message="Sync job completed.")


def run_import():
    devices = get_devices()
    if devices is not None:
        start_device_import()
        import_devices(devices)
        process_import()
        return 'done'
    else:
        return 'none'


def handle_parted():
    parted_qs = SlurpitImportedDevice.objects.exclude(
        slurpit_id__in=SlurpitStagedDevice.objects.values('slurpit_id')
    )
    
    count = 0
    for device in parted_qs:
        if device.mapped_device is None:
            device.delete()
        # elif device.mapped_device.status == status_offline():
        #     continue
        # else:
        #     device.mapped_device.status=status_offline()
        #     device.mapped_device.save()
        count += 1
    SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=f"Sync parted {count} devices")
    

def handle_new_comers():
    unattended = get_config('unattended_import')
    
    qs = SlurpitStagedDevice.objects.exclude(
        slurpit_id__in=SlurpitImportedDevice.objects.values('slurpit_id')
    )

    offset = 0
    count = len(qs)

    while offset < count:
        batch_qs = qs[offset:offset + BATCH_SIZE]
        to_import = []        
        for device in batch_qs:
            to_import.append(get_from_staged(device, unattended))
        SlurpitImportedDevice.objects.bulk_create(to_import, ignore_conflicts=True)
        offset += BATCH_SIZE

    SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=f"Sync imported {count} devices")

def handle_changed():
    latest_changeddate_subquery = SlurpitImportedDevice.objects.filter(
        slurpit_id=OuterRef('slurpit_id')
    ).order_by('-changeddate').values('changeddate')[:1]
    qs = SlurpitStagedDevice.objects.annotate(
        latest_changeddate=Subquery(latest_changeddate_subquery)
    ).filter(
        changeddate__gt=F('latest_changeddate')
    )
    offset = 0
    count = len(qs)

    while offset < count:
        batch_qs = qs[offset:offset + BATCH_SIZE]
        to_import = []        
        for device in batch_qs:
            result = SlurpitImportedDevice.objects.get(slurpit_id=device.slurpit_id)
            result.copy_staged_values(device)
            result.save()
            get_create_dcim_objects(device)
            if result.mapped_device:
                if device.disabled == False:
                    if result.mapped_device.status==status_offline():
                        result.mapped_device.status=status_inventory()
                else:
                    if result.mapped_device.status != status_offline():
                        result.mapped_device.status=status_offline()

                    
                set_device_custom_fields(result.mapped_device, {
                    'slurpit_hostname': device.hostname,
                    'slurpit_fqdn': device.fqdn,
                    'slurpit_ipv4': device.ipv4,
                })   
                
                if device.ipv4:
                    interface = Interface.objects.filter(device=result.mapped_device)
                    if interface:
                        interface = interface.first()
                    else:
                        interface = Interface.objects.create(name='management1', device=result.mapped_device, type='other')

                    address = f'{device.ipv4}/32'
                    ipaddress = IPAddress.objects.filter(address=address)
                    if ipaddress:
                        ipaddress = ipaddress.first()
                    else:
                        ipaddress = IPAddress.objects.create(address=address, status='active')
                    
                    ipaddress.assigned_object = interface
                    ipaddress.save()
                    result.mapped_device.primary_ip4 = ipaddress

                result.mapped_device.name = device.hostname
                result.mapped_device.save()
        offset += BATCH_SIZE

    SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=f"Sync updated {count} devices")

def import_from_queryset(qs: QuerySet, **extra):
    count = len(qs)
    offset = 0

    while offset < count:
        batch_qs = qs[offset:offset + BATCH_SIZE]
        to_import = []        
        for device in batch_qs:
            device.mapped_device = get_dcim_device(device, **extra)
            to_import.append(device)
        SlurpitImportedDevice.objects.bulk_update(to_import, fields={'mapped_device_id'})
        offset += BATCH_SIZE

def get_dcim_device(staged: SlurpitStagedDevice | SlurpitImportedDevice, **extra) -> Device:
    kw = get_default_objects()
    cf = extra.pop(custom_field_data_name, {})
    interface_name = extra.pop('interface_name', 'management1')

    cf.update({
        'slurpit_hostname': staged.hostname,
        'slurpit_fqdn': staged.fqdn,
        'slurpit_platform': staged.device_os,
        'slurpit_manufacturer': staged.brand,
        'slurpit_devicetype': staged.device_type,
        'slurpit_ipv4': staged.ipv4
    })    

    try:
        platform = Platform.objects.get(name=staged.device_os)
    except:
        platform = Platform.objects.get(slug=slugify(staged.device_os))
    
    devicetype = None
    if 'device_type' in extra:
        devicetype = extra['device_type']
        staged.mapped_devicetype = extra['device_type']
        staged.save()

    elif 'device_type' not in extra and staged.mapped_devicetype is not None:
        devicetype = staged.mapped_devicetype
    
    if devicetype:
        platform = devicetype.default_platform
        
    kw.update({
        'name': staged.hostname,
        'platform': platform,
        custom_field_data_name: cf,
        **extra,
        # 'primary_ip4_id': int(ip_address(staged.fqdn)),
    })
    if 'device_type' not in extra and staged.mapped_devicetype is not None:
        kw['device_type'] = staged.mapped_devicetype
        
    if staged.disabled == False:
        kw.setdefault('status', status_inventory())
    else:
        kw.setdefault('status', status_offline())
    
    device = Device.objects.filter(name=staged.hostname)

    if device:
        device = device.first()
        device.update(**kw)
    else:
        device = Device.objects.create(**kw)
    ensure_slurpit_tags(device)

    #Interface for new device.
    if staged.ipv4:
        interface, _ = Interface.objects.get_or_create(name=interface_name, device=device, defaults={'type':'other'})
        
        address = f'{staged.ipv4}/32'
        ipaddress = IPAddress.objects.filter(address=address)
        if ipaddress:
            ipaddress = ipaddress.first()
        else:
            ipaddress = IPAddress.objects.create(address=address, status='active')
        ipaddress.assigned_object = interface
        ipaddress.save()
        device.primary_ip4 = ipaddress
        device.save()
    
    return device

def get_from_staged(
        staged: SlurpitStagedDevice,
        add_dcim: bool
) -> SlurpitImportedDevice:
    device = SlurpitImportedDevice()
    device.copy_staged_values(staged)

    device.mapped_devicetype = get_create_dcim_objects(staged)
    if add_dcim:
        extra = {'device_type': device.mapped_devicetype} if device.mapped_devicetype else {}
        device.mapped_device = get_dcim_device(staged, **extra)
    return device


    
def get_latest_data_on_planning(hostname, planning_id):
    try:
        setting = SlurpitSetting.objects.get()
        uri_base = setting.server_url
        headers = {
                        'authorization': setting.api_key,
                        'useragent': f"{plugin_type}/requests",
                        'accept': 'application/json'
                    }
        uri_devices = f"{uri_base}/api/devices/snapshot/single/{hostname}/{planning_id}"

        r = requests.get(uri_devices, headers=headers, timeout=15, verify=False)
        # r.raise_for_status()
        if r.status_code != 200:
            return None

        data = r.json()
        log_message = f"Get the latest data from Slurp'it in {plugin_type.capitalize()} on planning ID."
        SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=log_message)
        return data
    except ObjectDoesNotExist:
        setting = None
        log_message = "Need to set the setting parameter"
        SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=log_message)
        return None

def import_plannings(plannings, delete=True):
    ids = {str(row['id']) : row for row in plannings if row['disabled'] == '0'}

    with transaction.atomic():
        if delete:
            count = SlurpitPlanning.objects.exclude(planning_id__in=ids.keys()).delete()[0]
            SlurpitSnapshot.objects.filter(planning_id__in=ids.keys()).delete()
            SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api parted {count} plannings")
    
        update_objects = SlurpitPlanning.objects.filter(planning_id__in=ids.keys())
        SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api updated {update_objects.count()} plannings")
        for planning in update_objects:
            obj = ids.pop(str(planning.planning_id))
            planning.name = obj['name']
            planning.comments = obj['comment']
            planning.save()
        
        to_save = []
        for obj in ids.values():
            to_save.append(SlurpitPlanning(name=obj['name'], comments=obj['comment'], planning_id=obj['id']))
        SlurpitPlanning.objects.bulk_create(to_save)
        
        SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api imported {len(to_save)} plannings")
        SlurpitLog.success(category=LogCategoryChoices.PLANNING, message=f"Sync job completed.")