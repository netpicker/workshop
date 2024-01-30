from core.choices import DataSourceStatusChoices
from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers

from slurpit_netbox.models import SlurpitPlanning, SlurpitImportedDevice, SlurpitStagedDevice, SlurpitLog, SlurpitSetting, SlurpitSnapshot, SlurpitMapping

__all__ = (
    'SlurpitPlanningSerializer',
    'SlurpitStagedDeviceSerializer',
    'SlurpitImportedDeviceSerializer',
    'SlurpitLogSerializer',
    'SlurpitSettingSerializer',
    'SlurpitSnapshotSerializer'
)

class SlurpitPlanningSerializer(NetBoxModelSerializer):
    id = serializers.IntegerField(source='planning_id')
    comment = serializers.CharField(source='comments')

    class Meta:
        model = SlurpitPlanning
        fields = ['id', "name", "comment", "display"]

class SlurpitStagedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlurpitStagedDevice
        fields = '__all__'

class SlurpitSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlurpitSnapshot
        fields = '__all__'


class SlurpitImportedDeviceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='slurpit_id')
    class Meta:
        model = SlurpitImportedDevice
        fields = ['id', 'disabled', 'hostname', 'fqdn', 'ipv4', 'device_os', 'device_type', 'brand', 'createddate', 'changeddate']

class SlurpitLogSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitLog
        fields = '__all__'

class SlurpitSettingSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitSetting
        fields = '__all__'

class SlurpitMappingSerializer(NetBoxModelSerializer):
    class Meta:
        model = SlurpitMapping
        fields = '__all__'