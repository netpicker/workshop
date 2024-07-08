import json
from datetime import timedelta

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
from django.utils import timezone
from django.db.models import Q
from django.core.serializers import serialize

from .serializers import SlurpitPlanningSerializer, SlurpitSnapshotSerializer, SlurpitImportedDeviceSerializer, SlurpitPrefixSerializer, SlurpitInterfaceSerializer, SlurpitInitIPAddressSerializer
from ..validator import device_validator, ipam_validator, interface_validator, prefix_validator
from ..importer import process_import, import_devices, import_plannings, start_device_import, BATCH_SIZE
from ..management.choices import *
from ..views.datamapping import get_device_dict
from ..references import base_name 
from ..references.generic import status_offline, SlurpitViewSet, status_decommissioning
from ..references.imports import * 
from ..models import SlurpitPlanning, SlurpitSnapshot, SlurpitImportedDevice, SlurpitStagedDevice, SlurpitLog, SlurpitMapping, SlurpitInitIPAddress, SlurpitInterface, SlurpitPrefix
from ..filtersets import SlurpitPlanningFilterSet, SlurpitSnapshotFilterSet, SlurpitImportedDeviceFilterSet
from ..views.setting import sync_snapshot
from ipam.models import FHRPGroup, VRF, IPAddress, VLAN, Role, Prefix
from dcim.models import Interface, Site
from dcim.forms import InterfaceForm
from ipam.forms import IPAddressForm, PrefixForm
from tenancy.models import Tenant
from django.core.cache import cache

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

        cache_key1 = (
                f"slurpit_plan_{planning_id}_{hostname}_template"
            )
        cache_key2 = (
                f"slurpit_plan_{planning_id}_{hostname}_planning"
            )
        cache.delete(cache_key1)
        cache.delete(cache_key2)
        
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
    
    def create(self, request):

        try:
            items = []
            for record in request.data:
                if record['content']['template_result']:
                    items.append(SlurpitSnapshot(
                        hostname=record['hostname'], 
                        planning_id=record['planning_id'],
                        content=record['content']['template_result'], 
                        result_type="template_result"))
                
                if record['content']['planning_result']:
                    items.append(SlurpitSnapshot(
                        hostname=record['hostname'], 
                        planning_id=record['planning_id'],
                        content=record['content']['planning_result'], 
                        result_type="planning_result"))
            
            SlurpitSnapshot.objects.bulk_create(items, batch_size=BATCH_SIZE, ignore_conflicts=True)
            SlurpitLog.info(category=LogCategoryChoices.PLANNING, message=f"Created {len(items)} snapshots for Planning by API")

            
        except:
            return JsonResponse({'status': 'error'}, status=500)

        return JsonResponse({'status': 'success'}, status=200)

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
            Device.objects.select_related('slurpitimporteddevice').update(status=status_decommissioning())
            SlurpitStagedDevice.objects.all().delete()
            SlurpitImportedDevice.objects.filter(mapped_device__isnull=True).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['delete'], url_path='delete/(?P<hostname>[^/.]+)')
    def delete(self, request, *args, **kwargs):
        hostname_to_delete = kwargs.get('hostname')
        with transaction.atomic():
            to_delete = SlurpitImportedDevice.objects.filter(hostname=hostname_to_delete)
            Device.objects.filter(slurpitimporteddevice__in=to_delete).update(status=status_decommissioning())
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

        ids = [obj['id'] for obj in request.data]
        hostnames = [obj['hostname'] for obj in request.data]
        SlurpitStagedDevice.objects.filter(Q(hostname__in=hostnames) | Q(slurpit_id__in=ids)).delete()
        import_devices(request.data)        
        return JsonResponse({'status': 'success'})

    @action(detail=False, methods=['post'],  url_path='sync_start')
    def sync_start(self, request):
        threshold = timezone.now() - timedelta(days=1)
        SlurpitStagedDevice.objects.filter(createddate__lt=threshold).delete()
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
    

class SlurpitInterfaceView(SlurpitViewSet):
    queryset = SlurpitInterface.objects.all()

    def get_serializer_class(self):
        return SlurpitInterfaceSerializer
    
    def create(self, request):
        # Validate request Interface data
        errors = interface_validator(request.data)
        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        try:
            # Get initial values for Interface
            enable_reconcile = True
            initial_obj = SlurpitInterface.objects.filter(name='').values('module', 'type', 'speed', 'label', 'description', 'duplex', 'enable_reconcile').first()
            initial_interface_values = {}

            if initial_obj:
                enable_reconcile = initial_obj['enable_reconcile']
                del initial_obj['enable_reconcile']
                initial_interface_values = {**initial_obj}
            else:
                initial_interface_values = {
                    'type': "other",
                    'label': '',
                    'description': '',
                    'speed': 0,
                    'duplex': None,
                    'module': None
                }

                # device = None

                # if initial_interface_values['device'] is not None:
                #     device = Device.objects.get(name=initial_interface_values['device'])

                # initial_interface_values['device'] = device

            total_errors = {}
            insert_data = []
            update_data = []
            total_data = []
            duplicates = []
            # Form validation 
            for record in request.data[::-1]:
                unique_interface = f'{record["name"]}/{record["hostname"]}'

                if unique_interface in duplicates:
                    continue
                duplicates.append(unique_interface)

                obj = Interface()
                
                device = None
                try:
                    device = Device.objects.get(name=record['hostname'])
                except: 
                    device = None

                if device is None: 
                    continue
                record['device'] = device
                del record['hostname']
                
                new_data = {**initial_interface_values, **record}
                form = InterfaceForm(data=new_data, instance=obj)
                total_data.append(new_data)
                
                # Fail case
                if form.is_valid() is False:
                    form_errors = form.errors
                    error_list_dict = {}

                    for field, errors in form_errors.items():
                        error_list_dict[field] = list(errors)

                    # Duplicate Interface
                    keys = error_list_dict.keys()
                    
                    if len(keys) ==1 and '__all__' in keys and len(error_list_dict['__all__']) == 1 and error_list_dict['__all__'][0].endswith("already exists."):
                        update_data.append(new_data)
                        continue
                    if '__all__' in keys and len(error_list_dict['__all__']) == 1 and error_list_dict['__all__'][0].endswith("already exists."):
                        del error_list_dict['__all__']
                    
                    error_key = f'{new_data["name"]}({"Global" if new_data["device"] is None else new_data["device"]})'
                    total_errors[error_key] = error_list_dict

                    return JsonResponse({'status': 'error', 'errors': total_errors}, status=400)
                else:
                    insert_data.append(new_data)
       
            if enable_reconcile:
                batch_update_qs = []
                batch_insert_qs = []

                for item in total_data:
                    device = None

                    if item['device'] is not None:
                        device = Device.objects.get(name=item['device'])
                        
                    item['device'] = device

                    slurpit_interface_item = SlurpitInterface.objects.filter(name=item['name'], device=item['device'])
                    
                    if slurpit_interface_item:
                        slurpit_interface_item = slurpit_interface_item.first()

                        # Update
                        allowed_fields_with_none = {}
                        allowed_fields = {'duplex', 'label', 'description', 'speed', 'type', 'module'}

                        for field, value in item.items():
                            if field in allowed_fields and value is not None and value != "":
                                setattr(slurpit_interface_item, field, value)
                            if field in allowed_fields_with_none:
                                setattr(slurpit_interface_item, field, value)

                        batch_update_qs.append(slurpit_interface_item)
                    else:
                        obj = Interface.objects.filter(name=item['name'], device=item['device'])
                        fields = {'label', 'device', 'module', 'type', 'duplex', 'speed', 'description'}
                        not_null_fields = {'label', 'device', 'module', 'type', 'duplex', 'speed', 'description'}

                        new_interface = {}
                        if obj:
                            obj = obj.first()
                            old_interface = {}

                            for field in fields:
                                old_interface[field] = getattr(obj, field)
                                new_interface[field] = item[field]

                                if field in not_null_fields and (new_interface[field] is None or new_interface[field] == ""):
                                    new_interface[field] = old_interface[field]

                            if new_interface == old_interface:
                                continue
                        else:
                            for field in fields: 
                                new_interface[field] = item[field]

                        batch_insert_qs.append(SlurpitInterface(
                            name = item['name'], 
                            **new_interface
                        ))
                
                count = len(batch_insert_qs)
                offset = 0

                while offset < count:
                    batch_qs = batch_insert_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for interface_item in batch_qs:
                        to_import.append(interface_item)

                    SlurpitInterface.objects.bulk_create(to_import)
                    offset += BATCH_SIZE


                count = len(batch_update_qs)
                offset = 0
                while offset < count:
                    batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for interface_item in batch_qs:
                        to_import.append(interface_item)

                    SlurpitInterface.objects.bulk_update(to_import, 
                        fields={'label', 'speed', 'type', 'duplex', 'description', 'module'}
                    )
                    offset += BATCH_SIZE

            else:

                # Batch Insert
                count = len(insert_data)
                offset = 0
                while offset < count:
                    batch_qs = insert_data[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for interface_item in batch_qs:
                        to_import.append(Interface(**interface_item))
                    Interface.objects.bulk_create(to_import)
                    offset += BATCH_SIZE
                
                
                # Batch Update
                batch_update_qs = []
                for update_item in update_data:
                    item = Interface.objects.get(name=update_item['name'], device=update_item['device'])
                    
                    # Update
                    allowed_fields_with_none = {}
                    allowed_fields = {'duplex', 'label', 'speed', 'type', 'description', 'module'}

                    for field, value in update_item.items():
                        if field in allowed_fields and value is not None and value != "":
                            setattr(item, field, value)
                        if field in allowed_fields_with_none:
                            setattr(item, field, value)

                    batch_update_qs.append(item)

                
                count = len(batch_update_qs)
                offset = 0
                while offset < count:
                    batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for interface_item in batch_qs:
                        to_import.append(interface_item)

                    Interface.objects.bulk_update(to_import, 
                        fields={'label', 'speed', 'type', 'duplex', 'description', 'module'}
                    )
                    offset += BATCH_SIZE


            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'errors', 'errors': str(e)}, status=400)
        
class SlurpitIPAMView(SlurpitViewSet):
    queryset = IPAddress.objects.all()
    
    def get_serializer_class(self):
        return SlurpitInitIPAddressSerializer
    
    def create(self, request):
        # Validate request IPAM data
        errors = ipam_validator(request.data)
        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        vrf = None
        tenant = None

        try:
            # Get initial values for IPAM
            enable_reconcile = True
            initial_obj = SlurpitInitIPAddress.objects.filter(address=None).values('status', 'vrf', 'tenant', 'role', 'enable_reconcile', 'description').first()
            initial_ipaddress_values = {}
            vrf = None
            tenant = None
            if initial_obj:
                enable_reconcile = initial_obj['enable_reconcile']
                del initial_obj['enable_reconcile']
                initial_ipaddress_values = {**initial_obj}

                obj = SlurpitInitIPAddress.objects.filter(address=None).get()

                if initial_ipaddress_values['vrf'] is not None:
                    vrf = VRF.objects.get(pk=initial_ipaddress_values['vrf'])
                if initial_ipaddress_values['tenant'] is not None:
                    tenant = Tenant.objects.get(pk=initial_ipaddress_values['tenant'])

                initial_ipaddress_values['vrf'] = vrf
                initial_ipaddress_values['tenant'] = tenant

            else:
                initial_ipaddress_values['vrf'] = None
                initial_ipaddress_values['tenant'] = None
                initial_ipaddress_values['role'] = ''
                initial_ipaddress_values['description'] = ''
                initial_ipaddress_values['status'] = 'active'

            total_errors = {}
            insert_ips = []
            update_ips = []
            total_ips = []

            duplicates = []
            # Form validation 
            for record in request.data[::-1]:
                unique_ipaddress = f'{record["address"]}'

                if unique_ipaddress in duplicates:
                    continue
                duplicates.append(unique_ipaddress)

                obj = IPAddress()
                new_data = {**initial_ipaddress_values, **record}
                form = IPAddressForm(data=new_data, instance=obj)
                total_ips.append(new_data)
                
                # Fail case
                if form.is_valid() is False:
                    form_errors = form.errors
                    error_list_dict = {}

                    for field, errors in form_errors.items():
                        error_list_dict[field] = list(errors)

                    # Duplicate IP Address
                    keys = error_list_dict.keys()
                    
                    if len(keys) ==1 and 'address' in keys and len(error_list_dict['address']) == 1 and error_list_dict['address'][0].startswith("Duplicate"):
                        update_ips.append(new_data)
                        continue
                    if 'address' in keys and len(error_list_dict['address']) == 1 and error_list_dict['address'][0].startswith("Duplicate"):
                        del error_list_dict['address']
                    
                    error_key = f'{new_data["address"]}({"Global" if new_data["vrf"] is None else new_data["vrf"]})'
                    total_errors[error_key] = error_list_dict

                    return JsonResponse({'status': 'error', 'errors': total_errors}, status=400)
                else:
                    insert_ips.append(new_data)



            if enable_reconcile:
                batch_update_qs = []
                batch_insert_qs = []

                for item in total_ips:

                    slurpit_ipaddress_item = SlurpitInitIPAddress.objects.filter(address=item['address'], vrf=item['vrf'])
                    
                    if slurpit_ipaddress_item:
                        slurpit_ipaddress_item = slurpit_ipaddress_item.first()

                        allowed_fields_with_none = {'status'}
                        allowed_fields = {'role', 'tenant', 'dns_name', 'description'}

                        for field, value in item.items():
                            if field in allowed_fields and value is not None and value != "":
                                setattr(slurpit_ipaddress_item, field, value)
                            if field in allowed_fields_with_none:
                                setattr(slurpit_ipaddress_item, field, value)

                        batch_update_qs.append(slurpit_ipaddress_item)
                    else:
                        obj = IPAddress.objects.filter(address=item['address'], vrf=vrf)
                        fields = ['status', 'role', 'description', 'tenant', 'dns_name']
                        not_null_fields = {'role', 'description', 'tenant', 'dns_name'}
                        new_ipaddress = {}

                        if obj:
                            obj = obj.first()
                            old_ipaddress = {}
                            
                            for field in fields:
                                old_ipaddress[field] = getattr(obj, field)
                                new_ipaddress[field] = item[field]

                                if field in not_null_fields and (new_ipaddress[field] is None or new_ipaddress[field] == ""):
                                    new_ipaddress[field] = old_ipaddress[field]

                            if new_ipaddress == old_ipaddress:
                                continue
                        else:
                            for field in fields:
                                new_ipaddress[field] = item[field]
                        
                        obj = SlurpitInitIPAddress(
                            address = item['address'], 
                            vrf = vrf,
                            **new_ipaddress
                        )

                        batch_insert_qs.append(obj)
                
                count = len(batch_insert_qs)
                offset = 0

                while offset < count:
                    batch_qs = batch_insert_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for ipaddress_item in batch_qs:
                        to_import.append(ipaddress_item)

                    created_items = SlurpitInitIPAddress.objects.bulk_create(to_import)
                    offset += BATCH_SIZE



                count = len(batch_update_qs)
                offset = 0
                while offset < count:
                    batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for ipaddress_item in batch_qs:
                        to_import.append(ipaddress_item)

                    SlurpitInitIPAddress.objects.bulk_update(to_import, fields={'status', 'role', 'tenant', 'dns_name', 'description'})


                    offset += BATCH_SIZE
                
            else:
                # Batch Insert
                count = len(insert_ips)
                offset = 0
                while offset < count:
                    batch_qs = insert_ips[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for ipaddress_item in batch_qs:
                        to_import.append(IPAddress(**ipaddress_item))
                    IPAddress.objects.bulk_create(to_import)
                    offset += BATCH_SIZE
                
                # Batch Update
                batch_update_qs = []
                for update_item in update_ips:
                    item = IPAddress.objects.get(address=update_item['address'], vrf=update_item['vrf'])

                    # Update
                    allowed_fields_with_none = {'status'}
                    allowed_fields = {'role', 'tenant', 'dns_name', 'description'}

                    for field, value in update_item.items():
                        if field in allowed_fields and value is not None and value != "":
                            setattr(item, field, value)
                        if field in allowed_fields_with_none:
                            setattr(item, field, value)

                    batch_update_qs.append(item)

                count = len(batch_update_qs)
                offset = 0
                while offset < count:
                    batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for ipaddress_item in batch_qs:
                        to_import.append(ipaddress_item)

                    IPAddress.objects.bulk_update(to_import, fields={'status', 'role', 'tenant', 'dns_name', 'description'})
                    offset += BATCH_SIZE


            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'errors': str(e)}, status=400)
        


class SlurpitPrefixView(SlurpitViewSet):
    queryset = SlurpitPrefix.objects.all()

    def get_serializer_class(self):
        return SlurpitPrefixSerializer
    
    def create(self, request):
        # Validate request prefix data
        errors = prefix_validator(request.data)
        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        vrf = None
        site = None
        tenant = None
        vlan = None
        role = None
            
        try:
            # Get initial values for prefix
            enable_reconcile = True
            initial_obj = SlurpitPrefix.objects.filter(prefix=None).values('status', 'vrf', 'role', 'site', 'vlan', 'tenant', 'enable_reconcile', 'description').first()
            initial_prefix_values = {}

            if initial_obj:
                enable_reconcile = initial_obj['enable_reconcile']
                del initial_obj['enable_reconcile']
                initial_prefix_values = {**initial_obj}

                if initial_prefix_values['vrf'] is not None:
                    vrf = VRF.objects.get(pk=initial_prefix_values['vrf'])
                if initial_prefix_values['site'] is not None:
                    site = Site.objects.get(pk=initial_prefix_values['site'])
                if initial_prefix_values['tenant'] is not None:
                    tenant = Tenant.objects.get(pk=initial_prefix_values['tenant'])
                if initial_prefix_values['vlan'] is not None:
                    tenant = Tenant.objects.get(pk=initial_prefix_values['vlan'])
                if initial_prefix_values['role'] is not None:
                    role = Role.objects.get(pk=initial_prefix_values['role'])

                initial_prefix_values['vrf'] = vrf
                initial_prefix_values['site'] = site
                initial_prefix_values['tenant'] = tenant
                initial_prefix_values['vlan'] = vlan
                initial_prefix_values['role'] = role

            else:
                initial_prefix_values = {
                    'status': 'active',
                    'vrf': None,
                    'site': None,
                    'tenant': None,
                    'vlan': None,
                    'role': None,
                    'description': ''
                }

            total_errors = {}
            insert_data = []
            update_data = []
            total_data = []

            duplicates = []
            # Form validation 
            for record in request.data[::-1]:
                unique_prefix = f'{record["prefix"]}'

                if unique_prefix in duplicates:
                    continue
                duplicates.append(unique_prefix)

                obj = Prefix()
                if 'vrf' in record and len(record['vrf']) > 0:
                    vrf = VRF.objects.filter(name=record['vrf'])
                    if vrf:
                        record['vrf'] = vrf.first()
                    else:
                        vrf = VRF.objects.create(name=record['vrf'])
                        record['vrf'] = vrf
                else:
                    if 'vrf' in record:
                        del record['vrf']

                new_data = {**initial_prefix_values, **record}
                form = PrefixForm(data=new_data, instance=obj)
                total_data.append(new_data)
                
                # Fail case
                if form.is_valid() is False:
                    form_errors = form.errors
                    error_list_dict = {}

                    for field, errors in form_errors.items():
                        error_list_dict[field] = list(errors)

                    # Duplicate Prefix
                    keys = error_list_dict.keys()
                    
                    if len(keys) ==1 and 'prefix' in keys and len(error_list_dict['prefix']) == 1 and error_list_dict['prefix'][0].startswith("Duplicate"):
                        update_data.append(new_data)
                        continue
                    if 'prefix' in keys and len(error_list_dict['prefix']) == 1 and error_list_dict['prefix'][0].startswith("Duplicate"):
                        del error_list_dict['prefix']
                    
                    error_key = f'{new_data["prefix"]}({"Global" if new_data["vrf"] is None else new_data["vrf"]})'
                    total_errors[error_key] = error_list_dict

                    return JsonResponse({'status': 'error', 'errors': total_errors}, status=400)
                else:
                    insert_data.append(new_data)
        
            if enable_reconcile:
                batch_update_qs = []
                batch_insert_qs = []

                for item in total_data:

                    slurpit_prefix_item = SlurpitPrefix.objects.filter(prefix=item['prefix'], vrf=item['vrf'])
                    
                    if slurpit_prefix_item:
                        slurpit_prefix_item = slurpit_prefix_item.first()

                        allowed_fields_with_none = {'status'}
                        allowed_fields = {'role', 'tenant', 'site', 'vlan', 'vrf', 'description'}

                        for field, value in item.items():
                            if field in allowed_fields and value is not None and value != "":
                                setattr(slurpit_prefix_item, field, value)
                            if field in allowed_fields_with_none:
                                setattr(slurpit_prefix_item, field, value)

                        batch_update_qs.append(slurpit_prefix_item)
                    else:
                        obj = Prefix.objects.filter(prefix=item['prefix'], vrf=item['vrf'])
                        
                        fields = {'status', 'vrf', 'vlan', 'tenant', 'site', 'role', 'description'}
                        not_null_fields = {'vlan', 'tenant', 'site', 'role', 'description'}
                        
                        new_prefix = {}

                        if obj:
                            obj = obj.first()
                            old_prefix = {}
                            
                            for field in fields:
                                old_prefix[field] = getattr(obj, field)
                                new_prefix[field] = item[field]

                                if field in not_null_fields and (new_prefix[field] is None or new_prefix[field] == ""):
                                    new_prefix[field] = old_prefix[field]

                            if new_prefix == old_prefix:
                                continue
                        else:
                            for field in fields:
                                new_prefix[field] = item[field]

                        batch_insert_qs.append(SlurpitPrefix(
                            prefix = item['prefix'],
                            **new_prefix
                        ))
                
                count = len(batch_insert_qs)
                offset = 0

                while offset < count:
                    batch_qs = batch_insert_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for prefix_item in batch_qs:
                        to_import.append(prefix_item)

                    SlurpitPrefix.objects.bulk_create(to_import)
                    offset += BATCH_SIZE


                count = len(batch_update_qs)
                offset = 0
                while offset < count:
                    batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for prefix_item in batch_qs:
                        to_import.append(prefix_item)

                    SlurpitPrefix.objects.bulk_update(to_import, 
                        fields={'description', 'vrf', 'tenant', 'status', 'vlan', 'site', 'role'},
                    )
                    offset += BATCH_SIZE

            else:

                # Batch Insert
                count = len(insert_data)
                offset = 0
                while offset < count:
                    batch_qs = insert_data[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for prefix_item in batch_qs:
                        to_import.append(Prefix(**prefix_item))
                    Prefix.objects.bulk_create(to_import)
                    offset += BATCH_SIZE
                
                
                # Batch Update
                batch_update_qs = []
                for update_item in update_data:
                    item = Prefix.objects.get(prefix=update_item['prefix'], vrf=update_item['vrf'])
                    
                    # Update
                    allowed_fields_with_none = {'status'}
                    allowed_fields = {'role', 'tenant', 'site', 'vlan', 'description', 'vrf'}

                    for field, value in update_item.items():
                        if field in allowed_fields and value is not None and value != "":
                            setattr(item, field, value)
                        if field in allowed_fields_with_none:
                            setattr(item, field, value)
                    
                    batch_update_qs.append(item)

                
                count = len(batch_update_qs)
                offset = 0
                while offset < count:
                    batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for prefix_item in batch_qs:
                        to_import.append(prefix_item)

                    Prefix.objects.bulk_update(to_import, 
                        fields={
                            'description', 'vrf', 'tenant', 'status', 'vlan', 'site', 'role'
                        }
                    )
                    offset += BATCH_SIZE


            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'errors', 'errors': str(e)}, status=400)
 