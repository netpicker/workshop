from core.choices import DataSourceStatusChoices
from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from slurpit_netbox.models import SlurpitPlan, ImportedDevice, Planning, StagedDevice, Source, SlurpitLog, Setting, Snapshot

__all__ = (
    'SlurpitPlanSerializer',
    'StagedDeviceSerializer',
    'ImportedDeviceSerializer',
    'SourceSerializer',
    'PlanningSerializer',
    'SlurpitLogSerializer',
    'SettingSerializer',
    'SnapshotSerializer'
)

class SlurpitPlanSerializer(NetBoxModelSerializer):

    class Meta:
        model = SlurpitPlan
        fields = ["id", "name", "display", "plan_id"]

class StagedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StagedDevice
        fields = '__all__'

class SnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snapshot
        fields = '__all__'


class ImportedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportedDevice
        fields = '__all__'


class SourceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="core-api:datasource-detail")
    status = ChoiceField(choices=DataSourceStatusChoices, read_only=True)

    class Meta:
        model = Source
        fields = [
            "id",
            "url",
            "display",
            "name",
            "status",
            "description",
            "comments",
            "parameters",
            "created",
            "last_updated",
        ]


class PlanningSerializer(NetBoxModelSerializer):
    class Meta:
        model = Planning
        fields = '__all__'

class SlurpitLogSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitLog
        fields = '__all__'

class SettingSerializer(NetBoxModelSerializer):
    class Meta:
        model = Setting
        fields = '__all__'