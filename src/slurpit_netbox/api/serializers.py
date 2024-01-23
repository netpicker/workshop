from core.choices import DataSourceStatusChoices
from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from slurpit_netbox.models import SlurpitPlan, SlurpitImportedDevice, SlurpitPlanning, SlurpitStagedDevice, SlurpitSource, SlurpitLog, SlurpitSetting, SlurpitSnapshot

__all__ = (
    'SlurpitPlanSerializer',
    'SlurpitStagedDeviceSerializer',
    'SlurpitImportedDeviceSerializer',
    'SlurpitSourceSerializer',
    'SlurpitPlanningSerializer',
    'SlurpitLogSerializer',
    'SlurpitSettingSerializer',
    'SlurpitSnapshotSerializer'
)

class SlurpitPlanSerializer(NetBoxModelSerializer):

    class Meta:
        model = SlurpitPlan
        fields = ["id", "name", "display", "plan_id"]

class SlurpitStagedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlurpitStagedDevice
        fields = '__all__'

class SlurpitSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlurpitSnapshot
        fields = '__all__'


class SlurpitImportedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlurpitImportedDevice
        fields = '__all__'


class SlurpitSourceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="core-api:datasource-detail")
    status = ChoiceField(choices=DataSourceStatusChoices, read_only=True)

    class Meta:
        model = SlurpitSource
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


class SlurpitPlanningSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitPlanning
        fields = '__all__'

class SlurpitLogSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitLog
        fields = '__all__'

class SlurpitSettingSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitSetting
        fields = '__all__'