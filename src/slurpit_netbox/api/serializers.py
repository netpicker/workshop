from rest_framework import serializers

from slurpit_netbox.models import ImportedDevice, StagedDevice


class StagedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StagedDevice
        fields = '__all__'


class ImportedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportedDevice
        fields = '__all__'
