import django_tables2 as tables
from django_tables2.columns import BoundColumn

from netbox.tables import NetBoxTable, ChoiceFieldColumn, columns
from .models import ImportedDevice


def check_link(**kwargs):
    return {}


class ImportColumn(BoundColumn):
    pass


def importing(*args, **kwargs):
    raise Exception([args, kwargs])


class ImportedDeviceTable(NetBoxTable):
    actions = columns.ActionsColumn(actions=tuple())
    mapped_device__id = tables.BooleanColumn(yesno="✔, ", verbose_name='Mapped', linkify=False)

    class Meta(NetBoxTable.Meta):
        model = ImportedDevice
        fields = ('pk', 'id', 'hostname', 'fqdn', 'device_os', 'device_type', 'last_updated', 'mapped_device')
        default_columns = ('hostname', 'fqdn', 'device_os', 'device_type', 'last_updated', 'mapped_device')
