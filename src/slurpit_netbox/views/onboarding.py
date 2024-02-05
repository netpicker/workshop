import requests
from dcim.choices import DeviceStatusChoices
from dcim.models import  Manufacturer, Platform, DeviceType, Site, Device
from django.contrib import messages
from django.contrib.contenttypes.fields import GenericRel
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import transaction, connection
from django.db.models import ManyToManyField, ManyToManyRel, F, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
# from extras.signals import clear_webhooks
from netbox.views import generic
from utilities.exceptions import AbortRequest, PermissionsViolation
from utilities.forms import restrict_form_fields
from .. import get_config
from ..models import SlurpitImportedDevice, SlurpitLog, SlurpitSetting
from ..management.choices import *
from .. import forms, importer, models, tables
from ..importer import (
    get_dcim_device, import_from_queryset, run_import, get_devices, BATCH_SIZE, import_devices, process_import
)
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from django.db.models.fields.json import KeyTextTransform
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse


@method_decorator(slurpit_plugin_registered, name='dispatch')
class SlurpitImportedDeviceListView(generic.ObjectListView):
    conflicted_queryset = models.SlurpitImportedDevice.objects.filter(mapped_device_id__isnull=True, hostname__in=Device.objects.values('name'))
    to_onboard_queryset = models.SlurpitImportedDevice.objects.filter(mapped_device_id__isnull=True).exclude(pk__in=conflicted_queryset.values('pk'))
    onboarded_queryset = models.SlurpitImportedDevice.objects.filter(mapped_device_id__isnull=False)
    migrate_queryset = models.SlurpitImportedDevice.objects.filter(
                mapped_device_id__isnull=False
            ).annotate(
                slurpit_devicetype=KeyTextTransform('slurpit_devicetype', 'mapped_device__custom_field_data'),
                slurpit_hostname=KeyTextTransform('slurpit_hostname', 'mapped_device__custom_field_data'),
                slurpit_fqdn=KeyTextTransform('slurpit_fqdn', 'mapped_device__custom_field_data'),
                slurpit_platform=KeyTextTransform('slurpit_platform', 'mapped_device__custom_field_data'),
                slurpit_manufactor=KeyTextTransform('slurpit_manufactor', 'mapped_device__custom_field_data'),
                fdevicetype=F('device_type'),
                fhostname=F('hostname'),
                ffqdn=F('fqdn'),
                fdeviceos=F('device_os'),
                fbrand=F('brand')
            ).exclude(
                Q(slurpit_devicetype=F('fdevicetype')) & 
                Q(slurpit_hostname=F('fhostname')) & 
                Q(slurpit_fqdn=F('ffqdn')) & 
                Q(slurpit_platform=F('fdeviceos')) & 
                Q(slurpit_manufactor=F('fbrand'))
            )
    
    queryset = to_onboard_queryset
    table = tables.SlurpitImportedDeviceTable
    template_name = "slurpit_netbox/onboard_device.html"

    def get(self, request, *args, **kwargs):        
        self.queryset = self.to_onboard_queryset

        if request.GET.get('tab') == "migrate":
            self.queryset = self.migrate_queryset
            self.table = tables.MigratedDeviceTable
        elif request.GET.get('tab') == "conflicted":
            self.queryset = self.conflicted_queryset
            self.table = tables.SlurpitImportedDeviceTable
        elif request.GET.get('tab') == "onboarded":
            self.queryset = self.onboarded_queryset

        return super().get(request, *args, **kwargs)
    
    def post(self, request):
        pks = map(int, request.POST.getlist('pk'))
        qs = self.queryset.filter(pk__in=pks, mapped_device_id__isnull=True)
        import_from_queryset(qs)
        return redirect(request.path)

    def get_extra_context(self, request):
        appliance_type = ''
        connection_status = ''
        try:
            setting = SlurpitSetting.objects.get()
            server_url = setting.server_url
            api_key = setting.api_key
            appliance_type = setting.appliance_type
            connection_status = setting.connection_status
        except ObjectDoesNotExist:
            setting = None

        return {
            'to_onboard_count': self.to_onboard_queryset.count(),
            'onboarded_count': self.onboarded_queryset.count(),
            'migrate_count': self.migrate_queryset.count(),
            'conflicted_count': self.conflicted_queryset.count(),
            'appliance_type': appliance_type,
            'connection_status': connection_status
        }


@method_decorator(slurpit_plugin_registered, name='dispatch')
class SlurpitImportedDeviceOnboardView(generic.BulkEditView):
    template_name = 'slurpit_netbox/bulk_edit.html'
    queryset = models.SlurpitImportedDevice.objects.all()
    table = tables.SlurpitImportedDeviceTable
    model_form = forms.OnboardingForm
    form = forms.OnboardingForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['models_queryset'] = self.queryset
        return kwargs

    def post(self, request, **kwargs):
        model = self.queryset.model

        if request.POST.get('_all') and self.filterset is not None:
            pk_list = self.filterset(request.GET, self.queryset.values_list('pk', flat=True), request=request).qs
        else:
            pk_list = request.POST.getlist('pk')

        self.queryset = models.SlurpitImportedDevice.objects.filter(pk__in=pk_list)
        device_types = list(self.queryset.values_list('device_type').distinct())

        form = self.form(request.POST, initial={'pk': pk_list, 'device_types': device_types})
        restrict_form_fields(form, request.user)

        if '_apply' in request.POST:
            if form.is_valid():
                try:
                    with transaction.atomic():
                        updated_objects = self._update_objects(form, request)
                        if updated_objects:
                            msg = f'Onboarded {len(updated_objects)} {model._meta.verbose_name_plural}'
                            messages.success(self.request, msg)

                    return redirect(self.get_return_url(request))

                except ValidationError as e:
                    messages.error(self.request, ", ".join(e.messages))
                    # clear_webhooks.send(sender=self)

                except (AbortRequest, PermissionsViolation) as e:
                    form.add_error(None, e.message)
                    # clear_webhooks.send(sender=self)

        elif 'migrate' in request.GET:
            migrate = request.GET.get('migrate')
            if migrate == 'create':                
                for obj in self.queryset:
                    device = obj.mapped_device
                    obj.mapped_device = None
                    obj.save()
                    device.delete() #delete last to prevent cascade delete
            else:
                for obj in self.queryset:
                    device = obj.mapped_device
                    device.name = obj.hostname

                    device.custom_field_data['slurpit_hostname'] = obj.hostname
                    device.custom_field_data['slurpit_fqdn'] = obj.fqdn
                    device.custom_field_data['slurpit_platform'] = obj.device_os
                    device.custom_field_data['slurpit_manufactor'] = obj.brand
                    device.custom_field_data['slurpit_devicetype'] = obj.device_type  
                    device.custom_field_data['slurpit_ipv4'] = obj.ipv4                  

                    manu = Manufacturer.objects.get(name=obj.brand)
                    device.device_type = DeviceType.objects.get(model=obj.device_type, manufacturer=manu)
                    device.platform = Platform.objects.get(name=obj.device_os)
                    device.save()
                    obj.save()

                    log_message = f"Migration of onboarded device - {obj.hostname} successfully updated."
                    SlurpitLog.success(category=LogCategoryChoices.ONBOARD, message=log_message)
                
                msg = f'Migration is done successfully.'
                messages.success(self.request, msg)

                return redirect(self.get_return_url(request))

        elif 'conflicted' in request.GET:
            conflic = request.GET.get('conflicted')
            if conflic == 'create':
                Device.objects.filter(name__in=self.queryset.values('hostname')).delete()
            else:
                for obj in self.queryset:
                    device = Device.objects.filter(name__iexact=obj.hostname).first()
                    obj.mapped_device = device

                    device.custom_field_data['slurpit_hostname'] = obj.hostname
                    device.custom_field_data['slurpit_fqdn'] = obj.fqdn
                    device.custom_field_data['slurpit_platform'] = obj.device_os
                    device.custom_field_data['slurpit_manufactor'] = obj.brand
                    device.custom_field_data['slurpit_devicetype'] = obj.device_type
                    device.custom_field_data['slurpit_ipv4'] = obj.ipv4             

                    manu = Manufacturer.objects.get(name=obj.brand)
                    device.device_type = DeviceType.objects.get(model=obj.device_type, manufacturer=manu)
                    device.platform = Platform.objects.get(name=obj.device_os)
                    device.save()
                    obj.save()

                    log_message = f"Conflicted device resolved - {obj.hostname} successfully updated."
                    SlurpitLog.success(category=LogCategoryChoices.ONBOARD, message=log_message)
                
                msg = f'Conflicts successfully resolved.'
                messages.success(self.request, msg)

                return redirect(self.get_return_url(request))
                
        initial_data = {'pk': pk_list, 'device_types': device_types}
        for k, v in importer.get_defaults().items():
            initial_data.setdefault(k, str(v.id))
        initial_data.setdefault('status', DeviceStatusChoices.STATUS_INVENTORY)

        if len(device_types) > 1:
            initial_data['device_type'] = 'keep_original'
        if len(device_types) == 1 and (dt := DeviceType.objects.filter(model__iexact=device_types[0][0]).first()):
            initial_data['device_type'] = dt.id
        print(device_types)

        form = self.form(initial=initial_data)
        restrict_form_fields(form, request.user)
                
        # Retrieve objects being edited
        table = self.table(self.queryset.filter(mapped_device_id__isnull=True), orderable=False)
        if not table.rows:
            messages.warning(request, "No {} were selected.".format(model._meta.verbose_name_plural))
            log_message = "Failed to onboard since no devices were selected."
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.ONBOARD, message=log_message)
            return redirect(self.get_return_url(request))

        return render(request, self.template_name, {
            'model': model,
            'form': form,
            'table': table,
            'return_url': self.get_return_url(request),
            **self.get_extra_context(request),
        })

    def _update_objects(self, form, request):
        device_type = None
        if form.cleaned_data['device_type'] != 'keep_original':
            device_type = DeviceType.objects.filter(id=form.cleaned_data['device_type']).first()
        updated_objects = []
        data = {
            'role': form.cleaned_data['role'],
            'site': form.cleaned_data['site'],
            'location': form.cleaned_data['location'],
            'rack': form.cleaned_data['rack'],
            'position': form.cleaned_data['position'],
            'latitude': form.cleaned_data['latitude'],
            'longitude': form.cleaned_data['longitude'],
            'tenant': form.cleaned_data['tenant'],
            'description': form.cleaned_data['description'],
            'airflow': form.cleaned_data['airflow'],
        }
        for obj in self.queryset.filter(pk__in=form.cleaned_data['pk']):
            if obj.mapped_device_id is not None:
                continue

            dt = device_type
            if not device_type:
                dt = obj.mapped_devicetype
                
            device = get_dcim_device(obj, device_type=dt, **data)
            obj.mapped_device = device
            obj.save()
            updated_objects.append(obj)

            SlurpitLog.success(category=LogCategoryChoices.ONBOARD, message=f"Onboarded device - {obj.hostname} successfully.")

            # Take a snapshot of change-logged models
            if hasattr(device, 'snapshot'):
                device.snapshot()
            
            if form.cleaned_data.get('add_tags', None):
                device.tags.add(*form.cleaned_data['add_tags'])
            if form.cleaned_data.get('remove_tags', None):
                device.tags.remove(*form.cleaned_data['remove_tags'])

        return updated_objects


@method_decorator(slurpit_plugin_registered, name='dispatch')
class ImportDevices(View):
    def get(self, request, *args, **kwargs):
        offset = request.GET.get("offset", None)
        try:
            if offset is not None:
                offset = int(offset)
                devices = get_devices(offset)
                if devices is not None and len(devices) > 0:
                    import_devices(devices)
                    offset += len(devices)
                return JsonResponse({"action": "import", "offset": offset})
            
            result = process_import()
            messages.info(request, "Synced the devices from Slurp'it.")
            return JsonResponse({"action": "process"})
        except requests.exceptions.RequestException as e:
            messages.error(request, "An error occured during querying Slurp'it!")
            SlurpitLog.failure(category=LogCategoryChoices.ONBOARD, message=f"An error occured during querying Slurp'it! {e}")
        
        return JsonResponse({"action": "", "error": "ERROR"})
    

