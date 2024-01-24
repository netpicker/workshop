import logging
import requests
import yaml

from functools import partial
from subprocess import PIPE, Popen
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models import F, ExpressionWrapper, fields, QuerySet
from django.utils.text import slugify

from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site, Platform
from dcim.choices import DeviceStatusChoices

from . import get_config
from .models import SlurpitImportedDevice, SlurpitStagedDevice, ensure_slurpit_tags, SlurpitLog, SlurpitSetting
from .management.choices import *

log = logging.getLogger(__name__)


BATCH_SIZE = 256
columns = ('slurpit_id', 'disabled', 'hostname', 'fqdn', 'device_os', 'device_type', 'brand', 'createddate', 'changeddate')


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
            log.warning('Missing device type, cannot import %r', device)
            SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=f"Missing device type, cannot import device {device.get('hostname')}")
            continue
        device['slurpit_id'] = device.pop('id')
        
        try:
            device['createddate'] = datetime.strptime(device['createddate'], '%Y-%m-%d %H:%M:%S')
            device['changeddate'] = datetime.strptime(device['changeddate'], '%Y-%m-%d %H:%M:%S')            
        except ValueError:
            SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=f"Failed to convert to datetime, cannot import {device.get('hostname')}")
            log.warning(f'Failed to convert to datetime, cannot import {device}')
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

    device_types = map_new_devicetypes(qs)
    offset = 0
    count = len(qs)

    while offset < count:
        batch_qs = qs[offset:offset + BATCH_SIZE]
        to_import = []        
        for device in batch_qs:
            to_import.append(get_from_staged(device, device_types, unattended))
        SlurpitImportedDevice.objects.bulk_create(to_import, ignore_conflicts=True)
        offset += BATCH_SIZE

    SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message=f"Sync imported {count} devices")

def handle_changed():
    query = f"SELECT s.* FROM {SlurpitStagedDevice._meta.db_table} s INNER JOIN {SlurpitImportedDevice._meta.db_table} i ON s.hostname = i.hostname AND s.changeddate > i.changeddate"
    qs = SlurpitStagedDevice.objects.raw(query)
    offset = 0
    count = len(qs)

    while offset < count:
        batch_qs = qs[offset:offset + BATCH_SIZE]
        to_import = []        
        for device in batch_qs:
            result = SlurpitImportedDevice.objects.get(hostname=device.hostname)
            result.copy_staged_values(device)
            result.save()

            if result.mapped_device.status==DeviceStatusChoices.STATUS_OFFLINE:
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

def grep(where: str, what: str, options: str) -> list[str] | None:
    opt = [f"-{options}"] if options else []
    needle = rf"{what}\b"
    sub = Popen(['egrep', *opt, needle, where], stdout=PIPE, stderr=PIPE)
    out, err = sub.communicate()
    lines = out.decode().strip().split('\n')
    return [ln for ln in lines if ln]


def lookup_manufacturer(s: str) -> Manufacturer | None:
    manufacturer, new = Manufacturer.objects.get_or_create(name = s, slug=slugify(s))
    if new:
        ensure_slurpit_tags(manufacturer)
    return manufacturer


def create_devicetype(descriptor: dict) -> DeviceType | None:
    manufacturer = lookup_manufacturer(descriptor.get('manufacturer'))
    if manufacturer is None:
        return None
    kw = {k.attname: descriptor[k.attname] for k in DeviceType._meta.fields if k.attname in descriptor}
    dev_type = DeviceType.objects.create(manufacturer=manufacturer, **kw)
    SlurpitLog.info(category=LogCategoryChoices.ONBOARD, message="Created DeviceType.")
    ensure_slurpit_tags(dev_type)
    return dev_type


def get_library_devicetype(staged_type: str) -> dict | None:
    lib = get_config('DEVICETYPE_LIBRARY')
    if lib is None:
        return None
    found_files = grep(lib, staged_type, 'lri')
    cnt = len(found_files)
    if cnt == 0:
        return None
    if cnt == 1:
        info_file = found_files[0]
    else:
        for info_file in found_files:
            ... # try figure out something
        else:
            return None

    with open(info_file) as f:
        devtype = yaml.safe_load(f)
    return devtype


def lookup_device_type(staged_type: str) -> DeviceType | None:
    devtype = DeviceType.objects.filter(model__iexact=staged_type).first()
    if devtype is not None:
        return devtype
    descriptor = get_library_devicetype(staged_type)
    if descriptor is None:
        return None
    model = descriptor['model']
    devtype = DeviceType.objects.filter(model__iexact=model).first() or create_devicetype(descriptor)
    return devtype


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

    manu, _ = Manufacturer.objects.get_or_create(name=staged.brand)
    platform_defs = {'name': staged.device_os, 'slug': staged.device_os}
    platform, _ = Platform.objects.get_or_create(**platform_defs)
    devtype_slug = f'{staged.brand}-{staged.device_type}'
    devtype_defs = {'model': staged.device_type, 'manufacturer': manu, 'slug': devtype_slug, 'default_platform': platform}
    try:
        dtype, _ = DeviceType.objects.get_or_create(**devtype_defs)
    except:
        dtype, _ = DeviceType.objects.get_or_create(model=staged.device_type, manufacturer=manu)
        
    kw.update({
        'name': staged.hostname,
        'platform': platform,
        'custom_field_data': cf,
        'device_type': dtype,
        **extra,
        # 'primary_ip4_id': int(ip_address(staged.fqdn)),
    })
    kw.setdefault('status', DeviceStatusChoices.STATUS_INVENTORY)
    if not dtype:
        if staged_type := staged.device_type:
            if device_type := lookup_device_type(staged_type):
                kw.update(device_type=device_type)

    device = Device.objects.create(**kw)
    ensure_slurpit_tags(device)
    return device


def get_from_staged(
        staged: SlurpitStagedDevice,
        device_types: dict[str, DeviceType],
        add_dcim: bool
) -> SlurpitImportedDevice:
    device = SlurpitImportedDevice()
    device.copy_staged_values(staged)
    device.mapped_devicetype = device_types.get(staged.device_type)
    if add_dcim:
        extra = {'device_type': device.mapped_devicetype} if device.mapped_devicetype else {}
        device.mapped_device = get_dcim_device(staged, **extra)
    return device


def map_new_devicetypes(qs):
    staged = SlurpitStagedDevice.objects.values('device_type')
    imported = SlurpitImportedDevice.objects.values('device_type')
    qs = staged.distinct().difference(imported.distinct())
    return {dt['device_type']: lookup_device_type(dt['device_type']) for dt in qs}

