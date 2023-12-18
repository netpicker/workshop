import django_tables2 as tables
from django.utils.safestring import mark_safe
from django_tables2 import Column
from django_tables2.columns import BoundColumn
from django_tables2.columns.base import LinkTransform
from django_tables2.utils import Accessor
from django.utils.translation import gettext_lazy as _
from netbox.tables import NetBoxTable, ToggleColumn, columns


from .models import ImportedDevice, Planning, Source, SlurpitLog


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
        model = ImportedDevice
        fields = ('pk', 'id', 'hostname', 'fqdn','brand', 'IP', 'device_os', 'device_type', 'last_updated')
        default_columns = ('hostname', 'fqdn', 'device_os', 'brand' , 'device_type', 'last_updated')


class SourceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    # snapshot_count = tables.Column(verbose_name="Snapshots")
    tags = columns.TagColumn(url_name="core:datasource_list")

    class Meta(NetBoxTable.Meta):
        model = Source
        fields = (
            "pk",
            "id",
            "name",
            "description",
            "comments",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "description")


class PlanningTable(NetBoxTable):
    pk = columns.ToggleColumn(visible=True,
                              attrs={
        "td__input": {
            "onclick": lambda record: mark_safe(f'return {str(not record.disabled).lower()};'),
            "__x": lambda record: mark_safe('" checked "x__' if record.selected else ''),
        },
    })
    actions = columns.ActionsColumn(actions=[])
    exempt_columns = {}
    name = tables.Column()
    disabled = columns.BooleanColumn()

    class Meta(NetBoxTable.Meta):
        model = Planning
        fields = (
            "pk",
            "id",
            "name",
            "external_id",
            "description",
            "selected",
            "disabled",
            "comments",
        )
        default_columns = ("pk", "name", "external_id", "description")

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