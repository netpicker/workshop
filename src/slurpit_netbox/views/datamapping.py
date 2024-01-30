from django.views.generic import View
from ..models import SlurpitImportedDevice, SlurpitMapping, SlurpitLog, SlurpitSetting
from .. import forms, importer, models, tables
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from ..forms import SlurpitMappingForm, SlurpitDeviceForm
from ..management.choices import *
from django.contrib import messages
from dcim.models import Device
from django.forms.models import model_to_dict
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils.safestring import mark_safe

BATCH_SIZE = 128

def get_device_dict(instance):
    device_dict = model_to_dict(instance)
    # Assuming 'device_type' is a ForeignKey, for example.
    device_dict['device_type'] = str(instance.device_type)
    device_dict['platform'] = str(instance.platform)
    device_dict['primary_ip4'] = str(instance.primary_ip4)
    device_dict['primary_ip6'] = str(instance.primary_ip6)


    return device_dict

@method_decorator(slurpit_plugin_registered, name='dispatch')
class DataMappingView(View):
    template_name = "slurpit_netbox/data_mapping.html"
    app_label = "dcim"
    model_name = "device"

    def get(self, request):
        sync = request.GET.get('sync', None)
        tab = request.GET.get('tab', None)

        if sync is not None:
            # request_body = []

            netbox_devices = Device.objects.all()
            devices_array = [get_device_dict(device) for device in netbox_devices]

            objs = SlurpitMapping.objects.all()
            
            for device in devices_array:
                row = {}
                for obj in objs:
                    target_field = obj.target_field.split('|')[1]
                    row[obj.source_field] = str(device[target_field])
                # request_body.append(row)
            


                try:
                    setting = SlurpitSetting.objects.get()
                    uri_base = setting.server_url
                    headers = {
                                    'Authorization': f'Bearer {setting.api_key}',
                                    'useragent': 'netbox/requests',
                                    'accept': 'application/json',
                                    'Content-Type': 'application/json',
                                }

                    uri_devices = f"{uri_base}api/devices"
                    try:
                        r = requests.post(uri_devices, headers=headers, json=row)
                        r = r.json()
                        
                        if r['status'] != 200:
                            error_message = ''
                            for error in r["messages"]:
                                error_message += f'{error}: {r["messages"][error]} \r\n <br> '
                            messages.error(request, mark_safe(error_message))
                            return redirect(f'{request.path}?tab={tab}')
                    except:
                        pass

                    log_message = "Syncing the devices from slurp'it in Netbox."
                    SlurpitLog.info(category=LogCategoryChoices.DATA_MAPPING, message=log_message)

                except ObjectDoesNotExist:
                    setting = None
                    log_message = "Need to set the setting parameter"
                    SlurpitLog.failure(category=LogCategoryChoices.DATA_MAPPING, message=log_message)
                
            messages.success(request, "Sync from Netbox to Slurpit is done successfully.")
            return redirect(f'{request.path}?tab={tab}')


        form = [
        ]

        mappings = SlurpitMapping.objects.all()
        
        for mapping in mappings:
            form.append({
                "choice": mapping,
                "form": SlurpitMappingForm(choice_name=mapping, initial={"target_field": mapping.target_field})
            })

        new_form = SlurpitMappingForm(doaction="add")
        device_form = SlurpitDeviceForm()
        return render(
            request,
            self.template_name, 
            {
                "form": form,
                "new_form": new_form,
                "device_form": device_form
            }
        )
    
    def post(self, request):
        tab = request.GET.get('tab', None)

        if tab == "netbox_to_slurpit":
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

        return redirect(request.path)