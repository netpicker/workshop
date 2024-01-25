from core.choices import DataSourceStatusChoices
from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from slurpit_netbox.models import SlurpitPlanning, SlurpitImportedDevice, SlurpitStagedDevice, SlurpitLog, SlurpitSetting, SlurpitSnapshot

__all__ = (
    'SlurpitPlanningSerializer',
    'SlurpitStagedDeviceSerializer',
    'SlurpitImportedDeviceSerializer',
    'SlurpitLogSerializer',
    'SlurpitSettingSerializer',
    'SlurpitSnapshotSerializer'
)

class SlurpitPlanningSerializer(NetBoxModelSerializer):

    class Meta:
        model = SlurpitPlanning
        fields = ["id", "name", "display", "planning_id"]

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

class SlurpitLogSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitLog
        fields = '__all__'

class SlurpitSettingSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitSetting
        fields = '__all__'