import requests

from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models import QuerySet
from django.utils.text import slugify
from django.utils import timezone
from django.db.models.expressions import RawSQL

from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site, Platform
from dcim.choices import DeviceStatusChoices
from ipam.models import *

from . import get_config
from .models import SlurpitImportedDevice, SlurpitStagedDevice, ensure_slurpit_tags, SlurpitLog, SlurpitSetting
from .management.choices import *

BATCH_SIZE = 256
columns = ('slurpit_id', 'disabled', 'hostname', 'fqdn', 'ipv4', 'device_os', 'device_type', 'brand', 'createddate', 'changeddate')


def get_devices():
    try:
        setting = SlurpitSetting.objects.get()
        uri_base = setting.server_url
        headers = {
                        'authorization': setting.api_key,
                        'useragent': 'netbox/requests',
                        'accept': 'application/json'
                    }
        uri_devices = f"{uri_base}/api/devices"
        r = requests.get(uri_devices, headers=headers)
        r.raise_for_status()
        data = r.json()
        log_message = "Syncing the devices from slurp'it in Netbox."
        SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=log_message)
        return data
    except ObjectDoesNotExist:
        setting = None
        log_message = "Need to set the setting parameter"
        SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=log_message)
        return None
    
def get_latest_data_on_planning(hostname, planning_id):
    try:
        setting = SlurpitSetting.objects.get()
        uri_base = setting.server_url
        headers = {
                        'authorization': setting.api_key,
                        'useragent': 'netbox/requests',
                        'accept': 'application/json'
                    }
        uri_devices = f"{uri_base}/api/devices/snapshot/single/{hostname}/{planning_id}"

        r = requests.get(uri_devices, headers=headers)
        r.raise_for_status()
        data = r.json()
        log_message = "Get the latest data from slurp'it in Netbox on planning ID."
        SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=log_message)
        return data
    except ObjectDoesNotExist:
        setting = None
        log_message = "Need to set the setting parameter"
        SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=log_message)
        return None


def get_defaults():
    device_type = DeviceType.objects.get(**get_config('DeviceType'))
    role = DeviceRole.objects.get(**get_config('DeviceRole'))
    site = Site.objects.get(**get_config('Site'))

    return {
        'device_type': device_type,
        'role': role,
        'site': site,
    }


def import_devices(devices):
    with connection.cursor() as cursor:
        cursor.execute(f"truncate {SlurpitStagedDevice._meta.db_table} cascade")
    to_insert = []
    for device in devices:
        if device.get('disabled') == '1':
            continue
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
        elif device.mapped_device.status == DeviceStatusChoices.STATUS_OFFLINE:
            continue
        else:
            device.mapped_device.status=DeviceStatusChoices.STATUS_OFFLINE
            device.mapped_device.save()
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
    qs = SlurpitStagedDevice.objects.filter(id__in=RawSQL("SELECT s.id FROM slurpit_netbox_slurpitstageddevice s INNER JOIN slurpit_netbox_slurpitimporteddevice i ON s.slurpit_id = i.slurpit_id AND s.changeddate > i.changeddate"))
    offset = 0
    count = len(qs)

    while offset < count:
        batch_qs = qs[offset:offset + BATCH_SIZE]
        to_import = []        
        for device in batch_qs:
            result = SlurpitImportedDevice.objects.get(slurpit_id=device.slurpit_id)
            result.copy_staged_values(device)
            result.save()

            if result.mapped_device and result.mapped_device.status==DeviceStatusChoices.STATUS_OFFLINE:
                result.mapped_device.status=DeviceStatusChoices.STATUS_INVENTORY
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
    kw = get_defaults()
    cf = extra.pop('custom_field_data', {})
    cf.update({
        'slurpit_hostname': staged.hostname,
        'slurpit_fqdn': staged.fqdn,
        'slurpit_platform': staged.device_os,
        'slurpit_manufactor': staged.brand,
        'slurpit_devicetype': staged.device_type
    })    
        
    kw.update({
        'name': staged.hostname,
        'platform': Platform.objects.get(name=staged.device_os),
        'custom_field_data': cf,
        'device_type': staged.mapped_devicetype,
        **extra,
        # 'primary_ip4_id': int(ip_address(staged.fqdn)),
    })
    kw.setdefault('status', DeviceStatusChoices.STATUS_INVENTORY)
    device = Device.objects.create(**kw)
    ensure_slurpit_tags(device)
    return device


def get_from_staged(
        staged: SlurpitStagedDevice,
        add_dcim: bool
) -> SlurpitImportedDevice:
    device = SlurpitImportedDevice()
    device.copy_staged_values(staged)

    manu, new = Manufacturer.objects.get_or_create(name=staged.brand, slug=slugify(staged.brand))
    if new:
        ensure_slurpit_tags(manu)
    platform, new = Platform.objects.get_or_create(name=staged.device_os, slug=staged.device_os)
    dtype, new = DeviceType.objects.get_or_create(model=staged.device_type, manufacturer=manu, slug=f'{staged.brand}-{staged.device_type}', default_platform=platform)
    if new:
        ensure_slurpit_tags(dtype)

    device.mapped_devicetype = dtype
    if add_dcim:
        extra = {'device_type': device.mapped_devicetype} if device.mapped_devicetype else {}
        device.mapped_device = get_dcim_device(staged, **extra)
    return device

