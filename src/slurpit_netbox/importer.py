import logging
from functools import partial
from hashlib import md5
from subprocess import PIPE, Popen
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
import arrow
import requests
import yaml

from dcim.models import (
    Device, DeviceRole, DeviceType, Manufacturer, Site, Platform
)
from dcim.choices import DeviceStatusChoices
from django.db.models import QuerySet
from django.utils.text import slugify

from . import get_config
from .models import ImportedDevice, StagedDevice, ensure_slurpit_tags, fmt_digest, SlurpitLog, Setting
from .management.choices import *

log = logging.getLogger(__name__)


BATCH_SIZE = 128
fields = ('id', 'digest', 'hostname', 'fqdn', 'device_os', 'device_type', 'brand', 'disabled',
          'added', 'last_seen', 'createddate', 'changeddate')


def get_devices():
    try:
        setting = Setting.objects.get()
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
        SlurpitLog.objects.create(level=LogLevelChoices.LOG_INFO, category=LogCategoryChoices.ONBOARD, message=log_message)
        return data
    except ObjectDoesNotExist:
        setting = None
        log_message = "Need to set the setting parameter"
        SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.ONBOARD, message=log_message)
        return None
    
def get_latest_data_on_planning(hostname, planning_id):
    try:
        setting = Setting.objects.get()
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
        print(data)
        log_message = "Get the latest data from slurp'it in Netbox on planning ID."
        SlurpitLog.objects.create(level=LogLevelChoices.LOG_INFO, category=LogCategoryChoices.ONBOARD, message=log_message)
        return data
    except ObjectDoesNotExist:
        setting = None
        log_message = "Need to set the setting parameter"
        SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.ONBOARD, message=log_message)
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
        cursor.execute(f"truncate {StagedDevice._meta.db_table} cascade")
    for device in devices:
        if device.get('device_type') is None:
            log.warning('Missing device type, cannot import %r', device)
            log_message = f"Missing device type, cannot import device - {device.get('hostname')}"
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.ONBOARD, message=log_message)
        plain = fmt_digest.format(**device).encode()
        digest = md5(plain).hexdigest()
        for tsf in ('last_seen', 'createddate', 'changeddate'):
            dt = device[tsf]
            device[tsf] = arrow.get(dt).datetime if dt else dt
        StagedDevice.objects.create(digest=digest, **device)

        log_message = f"Created/Updated device - {device.get('hostname')}."
        SlurpitLog.objects.create(level=LogLevelChoices.LOG_INFO, category=LogCategoryChoices.ONBOARD, message=log_message)


def process_import():
    unattended = get_config('unattended_import')
    handle_parted()
    handle_changed()
    handle_new_comers(unattended)


def run_import():
    devices = get_devices()
    if devices is not None:
        import_devices(devices)
        process_import()
        return 'done'
    else:
        return 'none'


def handle_parted():
    parted_qs = (
        ImportedDevice.objects.filter(mapped_device_id__isnull=False).only('id')
        .difference(StagedDevice.objects.only('id'))
    )
    Device.objects.filter(id__in=parted_qs).update(status=DeviceStatusChoices.STATUS_OFFLINE)


def isplit(iter, n):
    while True:
        items = []
        try:
            for _ in range(n):
                items.append(next(iter))
        except StopIteration:
            if items:
                yield items
            break
        else:
            yield items


def import_from_queryset(qs: QuerySet, **extra):
    def set_mapped(idev: ImportedDevice) -> ImportedDevice:
        idev.mapped_device = get_dcim(idev, **extra)
        return idev

    mapper = partial(set_mapped, **extra)
    for batch in isplit(map(mapper, qs), BATCH_SIZE):
        ImportedDevice.objects.bulk_update(batch, fields={'mapped_device_id'})


def grep(where: str, what: str, options: str) -> list[str] | None:
    opt = [f"-{options}"] if options else []
    needle = rf"{what}\b"
    sub = Popen(['egrep', *opt, needle, where], stdout=PIPE, stderr=PIPE)
    out, err = sub.communicate()
    lines = out.decode().strip().split('\n')
    return [ln for ln in lines if ln]


def lookup_manufacturer(s: str) -> Manufacturer | None:
    default = {'name': s}
    slug = slugify(s)
    manufacturer, new = Manufacturer.objects.get_or_create(default, slug=slug)
    if new:
        ensure_slurpit_tags(manufacturer)
    return manufacturer


def create_devicetype(descriptor: dict) -> DeviceType | None:
    manufacturer = lookup_manufacturer(descriptor.get('manufacturer'))
    if manufacturer is None:
        return None
    kw = {k.attname: descriptor[k.attname]
          for k in DeviceType._meta.fields if k.attname in descriptor}
    dev_type = DeviceType.objects.create(manufacturer=manufacturer, **kw)
    log_message = "Created DeviceType."
    SlurpitLog.objects.create(level=LogLevelChoices.LOG_INFO, category=LogCategoryChoices.ONBOARD, message=log_message)
    ensure_slurpit_tags(dev_type)
    return dev_type


def get_db_devicetype(staged_type: str) -> DeviceType | None:
    try:
        return DeviceType.objects.get(model__iexact=staged_type)
    except DeviceType.DoesNotExist:
        return None


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
    devtype = get_db_devicetype(staged_type)
    if devtype is not None:
        return devtype
    descriptor = get_library_devicetype(staged_type)
    if descriptor is None:
        return None
    model = descriptor['model']
    devtype = get_db_devicetype(model) or create_devicetype(descriptor)
    return devtype


def get_dcim(staged: StagedDevice | ImportedDevice, **extra) -> Device:
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
    platform_defs = {'name': staged.device_os}
    platform, _ = Platform.objects.get_or_create(platform_defs)
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
        staged: StagedDevice,
        device_types: dict[str, DeviceType],
        add_dcim: bool
) -> ImportedDevice:
    kw = {f: getattr(staged, f) for f in fields}
    dt = device_types.get(staged.device_type)
    if add_dcim:
        extra = {'device_type': dt} if dt else {}
        kw['mapped_device'] = get_dcim(staged, **extra)
    kw['mapped_devicetype'] = dt
    return ImportedDevice(**kw)


def map_new_devicetypes(qs):
    staged = StagedDevice.objects.values('device_type')
    imported = ImportedDevice.objects.values('device_type')
    qs = staged.distinct().difference(imported.distinct())
    result = {dt['device_type']: lookup_device_type(dt['device_type']) for dt in qs}
    return result


def handle_new_comers(unattended: bool):
    qs: QuerySet = (
        StagedDevice.objects.only(*fields)
        .difference(ImportedDevice.objects.only(*fields))
    )
    device_types = map_new_devicetypes(qs)
    mapper = partial(get_from_staged,
                     device_types=device_types, add_dcim=unattended)
    data = map(mapper, qs.iterator(BATCH_SIZE))
    for batch in isplit(data, BATCH_SIZE):
        try:
            ImportedDevice.objects.bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=True)
            ImportedDevice.objects.bulk_update(batch, {
                'device_type', 
                'changeddate',
                'hostname',
                'device_os',
                'fqdn'
            })
            
        except:
            pass

    log_message = "Sync job completed."
    SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.ONBOARD, message=log_message)


def handle_changed():
    # id's identical, digest changed -> update
    pass
