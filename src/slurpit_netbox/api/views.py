import json

from rest_framework.routers import APIRootView
from rest_framework_bulk import BulkCreateModelMixin, BulkDestroyModelMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status, mixins

from django.db import transaction
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict

from .serializers import SlurpitPlanningSerializer, SlurpitSnapshotSerializer, SlurpitImportedDeviceSerializer
from ..validator import device_validator
from ..importer import process_import, import_devices, import_plannings, start_device_import
from ..management.choices import *
from ..views.datamapping import get_device_dict
from ..references import base_name 
from ..references.generic import status_offline, SlurpitViewSet
from ..references.imports import * 
from ..models import SlurpitPlanning, SlurpitSnapshot, SlurpitImportedDevice, SlurpitStagedDevice, SlurpitLog, SlurpitMapping
from ..filtersets import SlurpitPlanningFilterSet, SlurpitSnapshotFilterSet, SlurpitImportedDeviceFilterSet


__all__ = (
    'SlurpitPlanningViewSet',
    'SlurpitRootView',
    'SlurpitDeviceView'
)

class SlurpitRootView(APIRootView):
    """
    Slurpit API root view
    """
    def get_view_name(self):
        return 'Slurpit'
    

class SlurpitPlanningViewSet(
        SlurpitViewSet
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
        import_plannings(request.data)
        return JsonResponse({'status': 'success'})
    
    def create(self, request):
        if not isinstance(request.data, list):
            return Response("Should be a list", status=status.HTTP_400_BAD_REQUEST)

        import_plannings(request.data, False)        
        return JsonResponse({'status': 'success'})

class SlurpitSnapshotViewSet(
        SlurpitViewSet,
        BulkCreateModelMixin,
        BulkDestroyModelMixin,
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
        SlurpitViewSet,
        BulkCreateModelMixin,
        BulkDestroyModelMixin,
    ):
    queryset = SlurpitImportedDevice.objects.all()
    serializer_class = SlurpitImportedDeviceSerializer
    filterset_class = SlurpitImportedDeviceFilterSet

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request, *args, **kwargs):
        with transaction.atomic():
            Device.objects.select_related('slurpitimporteddevice').update(status=status_offline())
            SlurpitStagedDevice.objects.all().delete()
            SlurpitImportedDevice.objects.filter(mapped_device__isnull=True).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['delete'], url_path='delete/(?P<hostname>[^/.]+)')
    def delete(self, request, *args, **kwargs):
        hostname_to_delete = kwargs.get('hostname')
        with transaction.atomic():
            to_delete = SlurpitImportedDevice.objects.filter(hostname=hostname_to_delete)
            Device.objects.filter(slurpitimporteddevice__in=to_delete).update(status=status_offline())
            to_delete.filter(mapped_device__isnull=True).delete()
            SlurpitStagedDevice.objects.filter(hostname=hostname_to_delete).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def create(self, request):
        errors = device_validator(request.data)
        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)
        if len(request.data) != 1:
            return JsonResponse({'status': 'error', 'errors': ['List size should be 1']}, status=400)
        
        start_device_import()
        import_devices(request.data)
        process_import(delete=False)
        
        return JsonResponse({'status': 'success'})
    
    @action(detail=False, methods=['post'],  url_path='sync')
    def sync(self, request):            
        errors = device_validator(request.data)
        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        import_devices(request.data)        
        return JsonResponse({'status': 'success'})

    @action(detail=False, methods=['post'],  url_path='sync_start')
    def sync_start(self, request):
        start_device_import()
        return JsonResponse({'status': 'success'})

    @action(detail=False, methods=['post'],  url_path='sync_end')
    def sync_end(self, request):
        process_import()
        return JsonResponse({'status': 'success'})
    
class SlurpitTestAPIView(SlurpitViewSet):
    queryset = SlurpitImportedDevice.objects.all()
    serializer_class = SlurpitImportedDeviceSerializer
    filterset_class = SlurpitImportedDeviceFilterSet

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='api')
    def api(self, request, *args, **kwargs):    
        return JsonResponse({'status': 'success'})
    
class SlurpitDeviceView(SlurpitViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    filterset_class = DeviceFilterSet


    @action(detail=False, methods=['get'], url_path='all')
    def all(self, request, *args, **kwargs):
        request_body = []

        devices_array = [get_device_dict(device) for device in Device.objects.all()]

        objs = SlurpitMapping.objects.all()
        
        for device in devices_array:
            row = {}
            for obj in objs:
                target_field = obj.target_field.split('|')[1]
                row[obj.source_field] = str(device[target_field])
            request_body.append(row)


        return JsonResponse({'data': request_body})
