
from netbox.api.viewsets import NetBoxModelViewSet
from dcim.models import Device
from dcim.choices import DeviceStatusChoices
from slurpit_netbox.models import SlurpitPlan, SlurpitSnapshot, SlurpitImportedDevice, SlurpitStagedDevice
from slurpit_netbox.filtersets import SlurpitPlanFilterSet, SlurpitSnapshotFilterSet, SlurpitImportedDeviceFilterSet
from .serializers import SlurpitPlanSerializer, SlurpitSnapshotSerializer, SlurpitImportedDeviceSerializer
from rest_framework.routers import APIRootView
from rest_framework_bulk import BulkCreateModelMixin, BulkDestroyModelMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.http import JsonResponse
import json
from ..validator import device_validator
from ..importer import process_import, import_devices
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

__all__ = (
    'SlurpitPlanViewSet',
    'SlurpitRootView',
)

class SlurpitRootView(APIRootView):
    """
    Slurpit API root view
    """
    def get_view_name(self):
        return 'Slurpit'
    
#
# Viewsets
#
class SlurpitPlanViewSet(
        BulkCreateModelMixin,
        BulkDestroyModelMixin,
        NetBoxModelViewSet
    ):
    queryset = SlurpitPlan.objects.all()
    serializer_class = SlurpitPlanSerializer
    filterset_class = SlurpitPlanFilterSet

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request, *args, **kwargs):
        """
        A custom action to delete all SlurpitPlan objects.
        Be careful with this operation: it cannot be undone!
        """
        # Perform the deletion and return a response
        self.queryset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def get_queryset(self):
        if self.request.method == 'GET':
            # Customize this queryset to suit your requirements for GET requests
            return SlurpitPlan.objects.filter(selected=True)
        # For other methods, use the default queryset
        return self.queryset
    
    @action(detail=False, methods=['delete'], url_path='delete/(?P<planning_id>[^/.]+)')
    def delete(self, request, *args, **kwargs):
        planning_id = kwargs.get('planning_id')
        SlurpitPlan.objects.filter(plan_id=planning_id).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class SlurpitSnapshotViewSet(
        BulkCreateModelMixin,
        BulkDestroyModelMixin,
        NetBoxModelViewSet
    ):
    queryset = SlurpitSnapshot.objects.all()
    serializer_class = SlurpitSnapshotSerializer
    filterset_class = SlurpitSnapshotFilterSet

    @action(detail=False, methods=['delete'], url_path='delete-all/(?P<hostname>[^/.]+)/(?P<planning_id>[^/.]+)')
    def delete_all(self, request, *args, **kwargs):
        """
        A custom action to delete all SlurpitPlan objects.
        Be careful with this operation: it cannot be undone!
        """
        hostname = kwargs.get('hostname')
        plan_id = kwargs.get('planning_id')

        if hostname and plan_id:
            self.queryset = SlurpitSnapshot.objects.filter(hostname=hostname, plan_id=plan_id)
            # Perform the deletion and return a response
            self.queryset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DeviceViewSet(
        BulkCreateModelMixin,
        BulkDestroyModelMixin,
        NetBoxModelViewSet
    ):
    queryset = SlurpitImportedDevice.objects.all()
    serializer_class = SlurpitImportedDeviceSerializer
    filterset_class = SlurpitImportedDeviceFilterSet

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request, *args, **kwargs):
        with transaction.atomic():
            Device.objects.select_related('slurpitimporteddevice').update(status=DeviceStatusChoices.STATUS_OFFLINE)
            SlurpitStagedDevice.objects.all().delete()
            SlurpitImportedDevice.objects.filter(mapped_device__isnull=True).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['delete'], url_path='delete/(?P<hostname>[^/.]+)')
    def delete(self, request, *args, **kwargs):
        hostname_to_delete = kwargs.get('hostname')
        with transaction.atomic():
            to_delete = SlurpitImportedDevice.objects.filter(hostname=hostname_to_delete)
            Device.objects.filter(slurpitimporteddevice__in=to_delete).update(status=DeviceStatusChoices.STATUS_OFFLINE)
            to_delete.filter(mapped_device__isnull=True).delete()
            SlurpitStagedDevice.objects.filter(hostname=hostname_to_delete).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def create(self, request):
        # Load JSON data from the request body
        devices = json.loads(request.body.decode('utf-8'))

        errors = device_validator(devices)

        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        import_devices(devices)
        process_import()
        
        return JsonResponse({'status': 'success'})
    
class SlurpitTestAPIView(NetBoxModelViewSet):
    queryset = SlurpitImportedDevice.objects.all()
    serializer_class = SlurpitImportedDeviceSerializer
    filterset_class = SlurpitImportedDeviceFilterSet

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='api')
    def api(self, request, *args, **kwargs):
    
        return JsonResponse({'status': 'success'})
