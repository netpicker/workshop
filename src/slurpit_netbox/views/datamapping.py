from django.views.generic import View
from ..models import SlurpitImportedDevice, SlurpitMapping, SlurpitLog
from .. import forms, importer, models, tables
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from ..forms import SlurpitMappingForm
from ..management.choices import *
from django.contrib import messages

@method_decorator(slurpit_plugin_registered, name='dispatch')
class DataMappingView(View):
    template_name = "slurpit_netbox/data_mapping.html"
    app_label = "dcim"
    model_name = "device"

    def get(self, request):
        form = [
            SlurpitMappingForm(choice_name="hostname"),
            SlurpitMappingForm(choice_name="fqdn"),
            SlurpitMappingForm(choice_name="ipv4"),
            SlurpitMappingForm(choice_name="device_os"),
            SlurpitMappingForm(choice_name="device_type"),
            SlurpitMappingForm(choice_name="disabled"),
        ]

        new_form = SlurpitMappingForm(doaction="add")
        return render(
            request,
            self.template_name, 
            {
                "form": form,
                "new_form": new_form,
            }
        )
    
    def post(self, request):
        tab = request.GET.get('tab', None)
        if tab == "netbox_to_slurpit":
            source_field = request.POST.get("source_field")
            target_field = request.POST.get("target_field")
            
            # try:
            #     obj= SlurpitMapping.objects.create(source_field=source_field, target_field=target_field)
            #     log_message =f'Added a mapping successfully that {source_field} converts to {target_field}.'      
            #     SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.DATA_MAPPING, message=log_message)
            #     messages.success(request, log_message)
            # except:
            #     log_message =f'Failted to add a mapping that {source_field} converts to {target_field}.'      
            #     SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.DATA_MAPPING, message=log_message)
            #     messages.error(request, log_message)
            #     pass
            
            return redirect(f'{request.path}?tab={tab}')
        
        return redirect(request.path)