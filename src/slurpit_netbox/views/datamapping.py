from django.views.generic import View
from ..models import (
    SlurpitImportedDevice, 
    SlurpitMapping, 
    SlurpitLog, 
    SlurpitSetting, 
    SlurpitInitIPAddress, 
    SlurpitInterface, 
    SlurpitPrefix,
    SlurpitVLAN
)
from .. import forms, importer, models, tables
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from ..forms import SlurpitMappingForm, SlurpitDeviceForm, SlurpitDeviceStatusForm, SlurpitInitIPAMForm, SlurpitDeviceInterfaceForm, SlurpitPrefixForm, SlurpitVLANForm
from ..management.choices import *
from django.contrib import messages
from dcim.models import Device
from django.forms.models import model_to_dict
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType
from extras.models import CustomField
from extras.models.tags import Tag
from ipam.models import IPRange
from urllib.parse import urlencode
from utilities.forms import restrict_form_fields
from utilities.exceptions import AbortRequest, PermissionsViolation
from django.db import router, transaction

BATCH_SIZE = 128

def get_device_dict(instance):
    device_dict = model_to_dict(instance)
    # Assuming 'device_type' is a ForeignKey, for example.
    device_dict['device_type'] = str(instance.device_type) if instance.device_type is not None else None
    device_dict['platform'] = str(instance.platform) if instance.platform is not None else None
    device_dict['primary_ip4'] = str(instance.primary_ip4) if instance.primary_ip4 is not None else None
    device_dict['primary_ip6'] = str(instance.primary_ip6) if instance.primary_ip6 is not None else None

    for custom_field in device_dict['custom_field_data']:
        device_dict[f'cf_{custom_field}'] = device_dict['custom_field_data'][custom_field]

    return device_dict

def post_slurpit_device(row, device_name):
    try:
        setting = SlurpitSetting.objects.get()
        uri_base = setting.server_url
        headers = {
                        'Authorization': f'Bearer {setting.api_key}',
                        'useragent': 'netbox/requests',
                        'accept': 'application/json',
                        'Content-Type': 'application/json',
                    }

        uri_devices = f"{uri_base}/api/devices/sync"
        
        try:
            row["ignore_plugin"] = str(1)
            r = requests.post(uri_devices, headers=headers, json=row, timeout=15, verify=False)
            r = r.json()
            r["device_name"] = device_name
            return r
        except Exception as e:
            return {"error": str(e), "device_name": device_name}

    except ObjectDoesNotExist:
        setting = None
        log_message = "Need to set the setting parameter"
        SlurpitLog.failure(category=LogCategoryChoices.DATA_MAPPING, message=log_message)

        return {"error": "Need to set the setting parameter", "device_name": device_name}
    
    return None

@method_decorator(slurpit_plugin_registered, name='dispatch')
class DataMappingView(View):
    template_name = "slurpit_netbox/data_mapping.html"
    app_label = "dcim"
    model_name = "device"

    def get(self, request):
        sync = request.GET.get('sync', None)
        tab = request.GET.get('tab', None)
        subtab = request.GET.get('subtab', None)
        if sync is not None:
            # request_body = []

            netbox_devices = Device.objects.all()
            devices_array = [get_device_dict(device) for device in netbox_devices]

            objs = SlurpitMapping.objects.all()
            
            for device in devices_array:
                row = {}
                for obj in objs:
                    target_field = obj.target_field.split('|')[1]
                    row[obj.source_field] = str(device[target_field]) if device[target_field] is not None else None

                    if obj.source_field == 'ipv4' or obj.source_field == 'fqdn':
                        row[obj.source_field] = row[obj.source_field].split('/')[0]
                # request_body.append(row)

                res = post_slurpit_device(row, device["name"])

                if res is None:
                    return redirect(f'{request.path}?tab={tab}')
                
                if res['status'] != 200:
                    for error in res["messages"]:
                        messages.error(request, f'{escape(error)}: {escape(res["messages"][error])}')

                    return redirect(f'{request.path}?tab={tab}')
                
            messages.success(request, "Sync from Netbox to Slurpit is done successfully.")
            return redirect(f'{request.path}?tab={tab}')


        form = [
        ]

        mappings = SlurpitMapping.objects.all()
        
        appliance_type = ''
        try:
            setting = SlurpitSetting.objects.get()
            appliance_type = setting.appliance_type
        except ObjectDoesNotExist:
            setting = None

        if tab == "devices":
            slurpit_tag = Tag.objects.get(name="slurpit")
            ip_ranges = IPRange.objects.filter(tags__in=[slurpit_tag])
        
        for mapping in mappings:
            form.append({
                "choice": mapping,
                "form": SlurpitMappingForm(choice_name=mapping, initial={"target_field": mapping.target_field})
            })

        new_form = SlurpitMappingForm(doaction="add")
        device_form = SlurpitDeviceForm()
        device_status_form = SlurpitDeviceStatusForm()


        if tab == "slurpit_to_netbox":
            if subtab == None or subtab == 'ipam':
                obj = SlurpitInitIPAddress.objects.filter(address=None).first()
                if obj is not None:
                    form = SlurpitInitIPAMForm(instance=obj)
                else:
                    form = SlurpitInitIPAMForm(data={'enable_reconcile':True})
            elif subtab == 'prefix':
                obj = SlurpitPrefix.objects.filter(prefix=None).first()
                if obj is not None:
                    form = SlurpitPrefixForm(instance=obj)
                else:
                    form = SlurpitPrefixForm(data={'enable_reconcile':True, 'status': 'active'})
            elif subtab == 'vlan':
                obj = SlurpitVLAN.objects.filter(name='').first()
                if obj is not None:
                    form = SlurpitVLANForm(instance=obj)
                else:
                    form = SlurpitVLANForm(data={'enable_reconcile':True, 'status': 'active'})
            else:
                obj = SlurpitInterface.objects.filter(name='').first()

                if obj is not None:
                    form = SlurpitDeviceInterfaceForm(instance=obj)
                else:
                    form = SlurpitDeviceInterfaceForm(data={'type': 'other', 'enable_reconcile':True})

        return render(
            request,
            self.template_name, 
            {
                "form": form,
                "new_form": new_form,
                "device_form": device_form,
                "device_status_form": device_status_form,
                "appliance_type": appliance_type,
            }
        )
    
    def post(self, request):
        tab = request.GET.get('tab', None)
        mapping_type = ''

        if tab == "netbox_to_slurpit" or tab is None:
            tab = "netbox_to_slurpit"
            test = request.POST.get('test')
            device_id = request.POST.get('device_id')

            if device_id is not None:
                if device_id == "":
                    return JsonResponse({})
                
                device = Device.objects.get(id=int(device_id))
                device = get_device_dict(device)

                row = {}
                objs = SlurpitMapping.objects.all()
                for obj in objs:
                    target_field = obj.target_field.split('|')[1]
                    row[obj.source_field] = str(device[target_field]) if device[target_field] is not None else None
                    
                    if obj.source_field == 'ipv4' or obj.source_field == 'fqdn':
                        row[obj.source_field] = row[obj.source_field].split('/')[0]
                    
                if test is not None:
                    res = post_slurpit_device(row, device["name"])

                    if res is None:
                        return JsonResponse({"error": "Server Internal Error."})
                    
                    return JsonResponse(res)

                return JsonResponse(row)
            
            action = request.POST.get("action")
            if action is None:
                source_field = request.POST.get("source_field")
                target_field = request.POST.get("target_field")
                
                try:
                    obj= SlurpitMapping.objects.create(source_field=source_field, target_field=target_field)
                    log_message =f'Added a mapping  which {source_field} field converts to {target_field} field.'      
                    SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.DATA_MAPPING, message=log_message)
                    messages.success(request, log_message)
                except Exception as e:
                    log_message =f'Failted to add a mapping which {source_field} field converts to {target_field} field.'      
                    SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.DATA_MAPPING, message=log_message)
                    messages.error(request, log_message)
                    pass
                
                return redirect(f'{request.path}?tab={tab}')
            
            elif action == "delete":
                source_field_keys = request.POST.getlist('pk')
                SlurpitMapping.objects.filter(source_field__in=source_field_keys).delete()
                return redirect(f'{request.path}?tab={tab}')
            
            elif action == "save":
                source_fields = request.POST.getlist('source_field')
                target_fields = request.POST.getlist('target_field')
                count = len(source_fields)
                offset = 0
                qs = []
                for i in range(count):
                    mapping, created = SlurpitMapping.objects.get_or_create(
                        source_field=source_fields[i], 
                        defaults={'target_field': target_fields[i]}
                    )
                    if not created:
                        # If the object was retrieved and not created, you will update its `target_field`
                        mapping.target_field = target_fields[i]
                    qs.append(mapping)

                while offset < count:
                    batch_qs = qs[offset:offset + BATCH_SIZE]
                    to_import = []        
                    for maping in batch_qs:
                        to_import.append(maping)

                    SlurpitMapping.objects.bulk_update(to_import, fields={'target_field'})
                    offset += BATCH_SIZE
                    
                return redirect(f'{request.path}?tab={tab}')
            elif action == "sync":
                device_status = request.POST.get('status')
                if device_status == "":
                    netbox_devices = Device.objects.all().values("id", "status")
                else:
                    netbox_devices = Device.objects.filter(status=device_status).values("id")
                device_names = []
                if netbox_devices:
                    for device in netbox_devices:
                        device_names.append(device['id'])
                
                return JsonResponse({"device": device_names})

        elif tab == "slurpit_to_netbox":
            mapping_type = request.POST.get('mappingtype')
            if mapping_type == 'ipam':
                obj = SlurpitInitIPAddress.objects.filter(address=None).first()
                if obj is None:
                    obj = SlurpitInitIPAddress()

                form = SlurpitInitIPAMForm(data=request.POST, instance=obj)
                restrict_form_fields(form, request.user)

                if form.is_valid():
                    try:
                        with transaction.atomic():
                            obj = form.save()
                            messages.success(request, "Updated the Slurpit IP Address Default values successfully.")
                    except (AbortRequest, PermissionsViolation) as e:
                        # logger.debug(e.message)
                        form.add_error(None, e.message)
                else:
                    messages.error(request, "Slurpit IP Address Form Validation Failed.")
                    pass
            elif mapping_type == 'interface':
                obj = SlurpitInterface.objects.filter(name='').first()
                if obj is None:
                    obj = SlurpitInterface()

                form = SlurpitDeviceInterfaceForm(data=request.POST, instance=obj)
                restrict_form_fields(form, request.user)

                if form.is_valid():
                    try:
                        with transaction.atomic():
                            obj = form.save()
                            messages.success(request, "Updated the Slurpit Interface Default values successfully.")
                    except (AbortRequest, PermissionsViolation) as e:
                        # logger.debug(e.message)
                        form.add_error(None, e.message)
                else:
                    messages.error(request, "Slurpit Interface Form Validation Failed.")
                    pass
            
            elif mapping_type == 'prefix':
                obj = SlurpitPrefix.objects.filter(prefix=None).first()
                if obj is None:
                    obj = SlurpitPrefix()

                form = SlurpitPrefixForm(data=request.POST, instance=obj)
                restrict_form_fields(form, request.user)

                if form.is_valid():
                    try:
                        with transaction.atomic():
                            obj = form.save()
                            messages.success(request, "Updated the Slurpit Prefix Default values successfully.")
                    except (AbortRequest, PermissionsViolation) as e:
                        # logger.debug(e.message)
                        form.add_error(None, e.message)
                else:
                    messages.error(request, "Slurpit Prefix Form Validation Failed.")
                    pass
            elif mapping_type == 'vlan':
                obj = SlurpitVLAN.objects.filter(name='').first()
                if obj is None:
                    obj = SlurpitVLAN()
                form = SlurpitVLANForm(data=request.POST, instance=obj)
                restrict_form_fields(form, request.user)

                if form.is_valid():
                    try:
                        with transaction.atomic():
                            obj = form.save()
                            messages.success(request, "Updated the Slurpit VLAN Default values successfully.")
                    except (AbortRequest, PermissionsViolation) as e:
                        # logger.debug(e.message)
                        form.add_error(None, e.message)
                else:
                    form_errors = form.errors
                    print(form_errors)
                    messages.error(request, "Slurpit VLAN Form Validation Failed.")

        base_url = request.path

        if mapping_type == "":
            query_string = urlencode({'tab': tab})
        else:
            query_string = urlencode({'tab': tab, 'subtab': mapping_type})
        url = f'{base_url}?{query_string}'
        return redirect(url)