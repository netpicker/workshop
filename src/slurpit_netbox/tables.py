import django_tables2 as tables
from django.forms import MultipleHiddenInput
from django.utils.safestring import mark_safe
from django_tables2 import Column
from django_tables2.columns import BoundColumn
from django_tables2.columns.base import LinkTransform
from django_tables2.utils import Accessor

from netbox.tables import NetBoxTable, ChoiceFieldColumn, ToggleColumn, columns
from .models import ImportedDevice


def check_link(**kwargs):
    return {}


class ImportColumn(BoundColumn):
    pass


def importing(*args, **kwargs):
    raise Exception([args, kwargs])


class ConditionalToggle(ToggleColumn):
    def render(self, value, bound_column, record):
        if record.mapped_device_id is None:
            result = super().render(value, bound_column, record)
            return mark_safe(result)
        return '✔'


class ConditionalLink(Column):
    def render(self, value, bound_column, record):
        if record.mapped_device_id is None:
            return value
        link = LinkTransform(attrs=self.attrs.get("a", {}), accessor=Accessor("mapped_device"))
        return link(value, value=value, record=record, bound_column=bound_column)


class DeviceTypeColumn(Column):
    def render(self, value, bound_column, record):
        if record.mapped_devicetype_id is None:
            return value
        link = LinkTransform(attrs=self.attrs.get("a", {}), accessor=Accessor("mapped_devicetype"))
        return link(value, value=value, record=record, bound_column=bound_column)


class ImportedDeviceTable(NetBoxTable):
    actions = columns.ActionsColumn(actions=tuple())
    pk = ConditionalToggle()
    hostname = ConditionalLink()
    device_type = DeviceTypeColumn()

    class Meta(NetBoxTable.Meta):
        model = ImportedDevice
        fields = ('pk', 'id', 'hostname', 'fqdn', 'device_os', 'device_type', 'last_updated')
        default_columns = ('hostname', 'fqdn', 'device_os', 'device_type', 'last_updated')
