from functools import partial
from hashlib import md5
from subprocess import PIPE, Popen

import arrow
import requests
import yaml

from django.db import connection


from dcim.models import (
    Device, DeviceRole, DeviceType, Manufacturer, Site
)
from dcim.choices import DeviceStatusChoices
from django.db.models import QuerySet

from . import get_config
from .models import ImportedDevice, StagedDevice, ensure_slurpit_tags, fmt_digest


BATCH_SIZE = 128


def get_devices():
    uri_base = get_config('API_ENDPOINT')
    headers = get_config('API_HEADERS')
    uri_devices = f"{uri_base}/api/devices"
    r = requests.get(uri_devices, headers=headers)
    r.raise_for_status()
    data = r.json()
    return data


def get_defaults():
    device_type = DeviceType.objects.get(**get_config('DeviceType'))
    role = DeviceRole.objects.get(**get_config('DeviceRole'))
    site = Site.objects.get(**get_config('Site'))

    return {
        'device_type': device_type,
        'role': role,
        'site': site,
    }


def import_devices():
    devices = get_devices()
    with connection.cursor() as cursor:
        cursor.execute(f"truncate {StagedDevice._meta.db_table} cascade")
    for device in devices:
        plain = fmt_digest.format(**device).encode()
        digest = md5(plain).hexdigest()
        for tsf in ('last_seen', 'createddate', 'changeddate'):
            device[tsf] = arrow.get(device[tsf]).datetime
        StagedDevice.objects.create(digest=digest, **device)
    return


def process_import():
    unattended = get_config('unattended_import')
    handle_parted()
    handle_changed()
    handle_new_comers(unattended)


def run_import():
    import_devices()
    process_import()


def handle_parted():
    parted_qs = (
        ImportedDevice.objects.filter(mapped_device_id__isnull=False).only('id')
        .difference(StagedDevice.objects.only('id'))
    )
    Device.objects.filter(id__in=parted_qs).update(status=DeviceStatusChoices.STATUS_OFFLINE)


fields = ('id', 'digest', 'hostname', 'fqdn', 'device_os', 'device_type', 'disabled',
          'added', 'last_seen', 'createddate', 'changeddate')


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
    sub = Popen(['grep', *opt, what, where], stdout=PIPE, stderr=PIPE)
    out, err = sub.communicate()
    return out.decode().strip().split('\n')


def lookup_manufacturer(s: str) -> Manufacturer | None:
    manufacturer, new = Manufacturer.objects.get_or_create(name=s)
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
    if not found_files or len(found_files) != 1:
        return None
    with open(found_files[0]) as f:
        devtype = yaml.safe_load(f)
    return devtype


def lookup_device_type(staged_type: str) -> DeviceType | None:
    devtype = get_db_devicetype(staged_type)
    if devtype is not None:
        return devtype
    descriptor = get_library_devicetype(staged_type)
    if descriptor is None:
        return None
    return create_devicetype(descriptor)


def get_dcim(staged: StagedDevice | ImportedDevice, **extra) -> Device:
    kw = get_defaults()
    cf = extra.pop('custom_field_data', {})
    cf.update({get_config('netmiko_handler'): staged.device_os})
    kw.update({
        'name': staged.hostname,
        'status': DeviceStatusChoices.STATUS_INVENTORY,
        'custom_field_data': cf,
        **extra,
        # 'primary_ip4_id': int(ip_address(staged.fqdn)),
    })
    if staged_type := staged.device_type:
        if device_type := lookup_device_type(staged_type):
            kw.update(device_type=device_type)
    device = Device.objects.create(**kw)
    return device


def get_from_staged(staged: StagedDevice, add_dcim: bool) -> ImportedDevice:
    kw = {f: getattr(staged, f) for f in fields}
    if add_dcim:
        kw['mapped_device'] = get_dcim(staged)
    return ImportedDevice(**kw)


def handle_new_comers(unattended: bool):
    qs = (
        StagedDevice.objects.only(*fields)
        .difference(ImportedDevice.objects.only(*fields))
    )
    mapper = partial(get_from_staged, add_dcim=unattended)
    data = map(mapper, qs.iterator(BATCH_SIZE))
    for batch in isplit(data, BATCH_SIZE):
        ImportedDevice.objects.bulk_create(batch, batch_size=BATCH_SIZE)


def handle_changed():
    # id's identical, digest changed -> update
    pass
