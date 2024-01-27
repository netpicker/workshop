
from netbox.api.viewsets import NetBoxModelViewSet
from dcim.models import Device
from dcim.choices import DeviceStatusChoices
from slurpit_netbox.models import SlurpitPlanning, SlurpitSnapshot, SlurpitImportedDevice, SlurpitStagedDevice
from slurpit_netbox.filtersets import SlurpitPlanningFilterSet, SlurpitSnapshotFilterSet, SlurpitImportedDeviceFilterSet
from .serializers import SlurpitPlanningSerializer, SlurpitSnapshotSerializer, SlurpitImportedDeviceSerializer
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
    'SlurpitPlanningViewSet',
    'SlurpitRootView',
)

class SlurpitRootView(APIRootView):
    """
    Slurpit API root view
    """
    def get_view_name(self):
        return 'Slurpit'
    

class SlurpitPlanningViewSet(
        NetBoxModelViewSet
    ):
    queryset = SlurpitPlanning.objects.all()
    serializer_class = SlurpitPlanningSerializer
    filterset_class = SlurpitPlanningFilterSet

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request, *args, **kwargs):
        """
        A custom action to delete all SlurpitPlanning objects.
        Be careful with this operation: it cannot be undone!
        """
        self.queryset.delete()
        SlurpitSnapshot.objects.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def get_queryset(self):
        if self.request.method == 'GET':
            # Customize this queryset to suit your requirements for GET requests
            return SlurpitPlanning.objects.filter(selected=True)
        # For other methods, use the default queryset
        return self.queryset
    
    @action(detail=False, methods=['delete'], url_path='delete/(?P<planning_id>[^/.]+)')
    def delete(self, request, *args, **kwargs):
        planning_id = kwargs.get('planning_id')
        SlurpitPlanning.objects.filter(planning_id=planning_id).delete()
        SlurpitSnapshot.objects.filter(planning_id=planning_id).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
        
    @action(detail=False, methods=['post'],  url_path='sync')
    def sync(self, request):
        if not isinstance(request.data, list):
            return Response("Should be a list", status=status.HTTP_400_BAD_REQUEST)

        ids = {row['id'] : row for row in request.data if row['disabled'] == '0'}

        update_objects = self.queryset.filter(planning_id__in=ids.keys())
        self.queryset.exclude(planning_id__in=ids.keys()).delete()
        SlurpitSnapshot.objects.filter(planning_id__in=ids.keys()).delete()
        
        for planning in update_objects:
            obj = ids.pop(planning.planning_id)
            planning.name = obj['name']
            planning.comments = obj['comment']
            planning.save()
        
        for obj in ids.values():
            planning = SlurpitPlanning()
            planning.name = obj['name']
            planning.comments = obj['comment']
            planning.planning_id = obj['id']
            planning.save()
        
        return JsonResponse({'status': 'success'})


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
        A custom action to delete all SlurpitPlanning objects.
        Be careful with this operation: it cannot be undone!
        """
        hostname = kwargs.get('hostname')
        planning_id = kwargs.get('planning_id')

        if hostname and planning_id:
            self.queryset = SlurpitSnapshot.objects.filter(hostname=hostname, planning_id=planning_id)
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
        errors = device_validator(request.data)

        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        import_devices(devices)
        process_import(delete=False)
        
        return JsonResponse({'status': 'success'})
    
class SlurpitTestAPIView(NetBoxModelViewSet):
    queryset = SlurpitImportedDevice.objects.all()
    serializer_class = SlurpitImportedDeviceSerializer
    filterset_class = SlurpitImportedDeviceFilterSet

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='api')
    def api(self, request, *args, **kwargs):
    
        return JsonResponse({'status': 'success'})
