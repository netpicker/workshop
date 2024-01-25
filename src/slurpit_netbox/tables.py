import django_tables2 as tables
from django.utils.safestring import mark_safe
from django_tables2 import Column
from django_tables2.columns import BoundColumn
from django_tables2.columns.base import LinkTransform
from django_tables2.utils import Accessor
from django.utils.translation import gettext_lazy as _
from netbox.tables import NetBoxTable, ToggleColumn, columns


from .models import SlurpitImportedDevice, SlurpitLog


def check_link(**kwargs):
    return {}


class ImportColumn(BoundColumn):
    pass


def importing(*args, **kwargs):
    raise Exception([args, kwargs])


class ConditionalToggle(ToggleColumn):
    def render(self, value, bound_column, record):
        if record.mapped_device_id is None or (
            record.mapped_device.custom_field_data['slurpit_devicetype'] != record.device_type or
            record.mapped_device.custom_field_data['slurpit_hostname'] != record.hostname or
            record.mapped_device.custom_field_data['slurpit_fqdn'] != record.fqdn or
            record.mapped_device.custom_field_data['slurpit_platform'] != record.device_os or 
            record.mapped_device.custom_field_data['slurpit_manufactor'] != record.brand
        ):
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


class SlurpitImportedDeviceTable(NetBoxTable):
    actions = columns.ActionsColumn(actions=tuple())
    pk = ConditionalToggle()
    hostname = ConditionalLink()
    device_type = DeviceTypeColumn()

    brand = tables.Column(
        verbose_name = _('Manufactor')
    )

    device_os = tables.Column(
        verbose_name = _('Platform')
    )

    last_updated = tables.Column(
        verbose_name = _('Last seen')
    )

    class Meta(NetBoxTable.Meta):
        model = SlurpitImportedDevice
        fields = ('pk', 'id', 'hostname', 'fqdn','brand', 'IP', 'device_os', 'device_type', 'last_updated')
        default_columns = ('hostname', 'fqdn', 'device_os', 'brand' , 'device_type', 'last_updated')

class MigratedDeviceTable(NetBoxTable):
    actions = columns.ActionsColumn(actions=tuple())
    pk = ConditionalToggle()
    hostname = ConditionalLink()
    device_type = DeviceTypeColumn()

    brand = tables.Column(
        verbose_name = _('Manufactor')
    )

    device_os = tables.Column(
        verbose_name = _('Platform')
    )

    last_updated = tables.Column(
        verbose_name = _('Last seen')
    )

    slurpit_devicetype = tables.Column(
        accessor='slurpit_device_type', 
        verbose_name='Original Device Type'
    )

    class Meta(NetBoxTable.Meta):
        model = SlurpitImportedDevice
        fields = ('pk', 'id', 'hostname', 'fqdn','brand', 'IP', 'device_os', 'device_type', 'slurpit_devicetype', 'last_updated')
        default_columns = ('hostname', 'fqdn', 'device_os', 'brand' , 'device_type', 'slurpit_devicetype', 'last_updated')


class LoggingTable(NetBoxTable):
    actions = columns.ActionsColumn(actions=tuple())
    level = tables.Column()
    class Meta(NetBoxTable.Meta):
        model = SlurpitLog
        fields = ( 'pk', 'id', 'log_time', 'level', 'category', 'message', 'last_updated')
        default_columns = ('log_time', 'level', 'category', 'message')
    
    def render_level(self, value, record):
        badge_class = {
            'Info': 'badge bg-info',
            'Success': 'badge bg-success',
            'Failure': 'badge bg-danger',
            # Add more mappings for other levels as needed
        }.get(value, 'badge bg-secondary')  # Default to secondary if level is not recognized

        badge_html = f'<span class="{badge_class}">{value}</span>'
        return mark_safe(badge_html)
    
class SlurpitPlanningTable(tables.Table):

    class Meta:
        attrs = {
            "class": "table table-hover object-list",
        }
        empty_text = _("No results found")

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)