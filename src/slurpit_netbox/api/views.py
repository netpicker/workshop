
from netbox.api.viewsets import NetBoxModelViewSet
from dcim.models import Device
from dcim.choices import DeviceStatusChoices
from slurpit_netbox.models import SlurpitPlanning, SlurpitSnapshot, SlurpitImportedDevice, SlurpitStagedDevice, SlurpitLog
from slurpit_netbox.filtersets import SlurpitPlanningFilterSet, SlurpitSnapshotFilterSet, SlurpitImportedDeviceFilterSet
from .serializers import SlurpitPlanningSerializer, SlurpitSnapshotSerializer, SlurpitImportedDeviceSerializer
from rest_framework.routers import APIRootView
from rest_framework_bulk import BulkCreateModelMixin, BulkDestroyModelMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction
from django.http import JsonResponse
import json
from ..validator import device_validator
from ..importer import process_import, import_devices
from ..management.choices import *

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
        SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api deleted all snapshots and plannings")
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
        planning = SlurpitPlanning.objects.filter(planning_id=planning_id).first()
        if not planning:
            return Response(f"Unknown planning id {planning_id}", status=status.HTTP_400_BAD_REQUEST)

        planning.delete()
        count = SlurpitSnapshot.objects.filter(planning_id=planning_id).delete()[0]
        SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api deleted all {count} snapshots and planning {planning.name}")
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    @action(detail=False, methods=['post'],  url_path='sync')
    def sync(self, request):
        if not isinstance(request.data, list):
            return Response("Should be a list", status=status.HTTP_400_BAD_REQUEST)
        self._handle_plannings(request.data)
        return JsonResponse({'status': 'success'})
    
    def create(self, request):
        if not isinstance(request.data, list):
            return Response("Should be a list", status=status.HTTP_400_BAD_REQUEST)

        self._handle_plannings(request.data, False)        
        return JsonResponse({'status': 'success'})

    def _handle_plannings(self, plannings, delete=True):
        ids = {str(row['id']) : row for row in plannings if row['disabled'] == '0'}

        with transaction.atomic():
            if delete:
                count = self.queryset.exclude(planning_id__in=ids.keys()).delete()[0]
                SlurpitSnapshot.objects.filter(planning_id__in=ids.keys()).delete()
                SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api parted {count} plannings")
        
            update_objects = self.queryset.filter(planning_id__in=ids.keys())
            SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api updated {update_objects.count()} plannings")
            for planning in update_objects:
                obj = ids.pop(str(planning.planning_id))
                planning.name = obj['name']
                planning.comments = obj['comment']
                planning.save()
            
            to_save = []
            for obj in ids.values():
                to_save.append(SlurpitPlanning(name=obj['name'], comments=obj['comment'], planning_id=obj['id']))
            SlurpitPlanning.objects.bulk_create(to_save)
            
            SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api imported {len(to_save)} plannings")
            SlurpitLog.success(category=LogCategoryChoices.PLANNING, message=f"Sync job completed.")

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
        planning_id = kwargs.get('planning_id')
        planning = SlurpitPlanning.objects.filter(planning_id=planning_id).first()
        if not planning:
            return Response(f"Unknown planning id {planning_id}", status=status.HTTP_400_BAD_REQUEST)
            
        hostname = kwargs.get('hostname')
        if not hostname:
            return Response(f"No hostname was given", status=status.HTTP_400_BAD_REQUEST)

        count = SlurpitSnapshot.objects.filter(hostname=hostname, planning_id=planning_id).delete()[0]

        SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api deleted all {count} snapshots for planning {planning.name} and hostname {hostname}")

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['delete'], url_path='clear/(?P<planning_id>[^/.]+)')
    def clear(self, request, *args, **kwargs):
        planning_id = kwargs.get('planning_id')
        planning = SlurpitPlanning.objects.filter(planning_id=planning_id).first()
        if not planning:
            return Response(f"Unknown planning id {planning_id}", status=status.HTTP_400_BAD_REQUEST)
        count = SlurpitSnapshot.objects.filter(planning_id=planning_id).delete()[0]
        SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Api deleted all {count} snapshots for planning {planning.name}")

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

        import_devices(request.data)
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
