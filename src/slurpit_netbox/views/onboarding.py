import logging
import requests
from dcim.choices import DeviceStatusChoices
from dcim.models import  Manufacturer, Platform, DeviceType, Site
from django.contrib import messages
from django.contrib.contenttypes.fields import GenericRel
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import ManyToManyField, ManyToManyRel, F, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
# from extras.signals import clear_webhooks
from netbox.views import generic
from utilities.exceptions import AbortRequest, PermissionsViolation
from utilities.forms import restrict_form_fields
from .. import get_config
from ..models import ImportedDevice, SlurpitLog, Setting
from ..management.choices import *
from .. import forms, importer, models, tables
from ..importer import (
    get_dcim_device, import_from_queryset, lookup_device_type, run_import
)
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from django.db.models.fields.json import KeyTextTransform
from django.core.exceptions import ObjectDoesNotExist


@method_decorator(slurpit_plugin_registered, name='dispatch')
class ImportedDeviceListView(generic.ObjectListView):
    to_onboard_queryset = models.ImportedDevice.objects.filter( mapped_device_id__isnull=True)
    onboarded_queryset = models.ImportedDevice.objects.filter( mapped_device_id__isnull=False)
    migrate_queryset = models.ImportedDevice.objects.filter(
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
    table = tables.ImportedDeviceTable
    template_name = "slurpit_netbox/onboard_device.html"

    def get(self, request, *args, **kwargs):        
        self.queryset = self.to_onboard_queryset

        if request.GET.get('tab') == "migrate":
            self.queryset = self.migrate_queryset
            self.table = tables.MigratedDeviceTable
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
        try:
            setting = Setting.objects.get()
            server_url = setting.server_url
            api_key = setting.api_key
            appliance_type = setting.appliance_type
        except ObjectDoesNotExist:
            setting = None

        return {
            'to_onboard_count': self.to_onboard_queryset.count(),
            'onboarded_count': self.onboarded_queryset.count(),
            'migrate_count': self.migrate_queryset.count(),
            'appliance_type': appliance_type,
        }


@method_decorator(slurpit_plugin_registered, name='dispatch')
class ImportedDeviceOnboardView(generic.BulkEditView):
    template_name = 'slurpit_netbox/bulk_edit.html'
    queryset = models.ImportedDevice.objects.all()
    table = tables.ImportedDeviceTable
    model_form = forms.OnboardingForm
    form = forms.OnboardingForm

    def post(self, request, **kwargs):
        logger = logging.getLogger(__name__)
        model = self.queryset.model

        if request.POST.get('_all') and self.filterset is not None:
            pk_list = self.filterset(request.GET, self.queryset.values_list('pk', flat=True), request=request).qs
        else:
            pk_list = request.POST.getlist('pk')

        self.queryset = models.ImportedDevice.objects.filter(pk__in=pk_list)

        form = self.form(request.POST, initial={'pk': pk_list})
        restrict_form_fields(form, request.user)

        if '_apply' in request.POST:
            if form.is_valid():
                logger.debug("Form validation was successful")
                try:
                    with transaction.atomic():
                        updated_objects = self._update_objects(form, request)
                        if updated_objects:
                            msg = f'Onboarded {len(updated_objects)} {model._meta.verbose_name_plural}'
                            logger.info(msg)
                            messages.success(self.request, msg)

                    return redirect(self.get_return_url(request))

                except ValidationError as e:
                    messages.error(self.request, ", ".join(e.messages))
                    # clear_webhooks.send(sender=self)

                except (AbortRequest, PermissionsViolation) as e:
                    logger.debug(e.message)
                    form.add_error(None, e.message)
                    # clear_webhooks.send(sender=self)

        else:
            if 'migrate' in request.GET:
                migrate = request.GET.get('migrate')
                return_flg = False

                for obj in self.queryset:
                    if migrate == 'create':
                        try:
                            obj.mapped_device.delete()
                            obj.mapped_device = None
                            obj.save()
                        except:
                            pass
                    else:
                        cf = obj.mapped_device.custom_field_data
                        cf['slurpit_hostname'] = obj.hostname
                        cf['slurpit_fqdn'] = obj.fqdn
                        cf['slurpit_platform'] = obj.device_os
                        cf['slurpit_manufactor'] = obj.brand
                        cf['slurpit_devicetype'] = obj.device_type

                        site = Site.objects.get()

                        obj.mapped_device.custom_field_data = cf
                        obj.mapped_device.device_type =  dtype
                        obj.mapped_device.platform = platform
                        obj.mapped_device.name = obj.hostname
                        obj.mapped_device.site = site
                        obj.mapped_device.save()
                        obj.save()

                        log_message = f"Migration of onboarded device - {obj.hostname} successfully updated."
                        SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.ONBOARD, message=log_message)

                        return_flg = True
                    
                if return_flg:
                    msg = f'Migration is done successfully.'
                    logger.info(msg)
                    messages.success(self.request, msg)

                    return redirect(self.get_return_url(request))

            defaults = importer.get_defaults()
            device_types = list(self.queryset.values_list('device_type').distinct())
            if len(device_types) == 1 and (dt := lookup_device_type(device_types[0][0])):
                defaults['device_type'] = dt
            initial_data = {'pk': pk_list}
            for k, v in defaults.items():
                initial_data.setdefault(k, str(v.id))
            initial_data.setdefault('status', DeviceStatusChoices.STATUS_INVENTORY)

            form = self.form(initial=initial_data)
            restrict_form_fields(form, request.user)
                
        # Retrieve objects being edited
        table = self.table(self.queryset.filter(mapped_device_id__isnull=True), orderable=False)
        if not table.rows:
            messages.warning(request, "No onboardable {} were selected.".format(model._meta.verbose_name_plural))
            log_message = "Failed onboarded since no onboardable device was selected."
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
        custom_fields = getattr(form, 'custom_fields', {})
        standard_fields = [
            field for field in form.fields if field not in list(custom_fields) + ['pk']
        ]
        nullified_fields = request.POST.getlist('_nullify')
        updated_objects = []    
        model_fields = {}
        m2m_fields = {}

        # Build list of model fields and m2m fields for later iteration
        for name in standard_fields:
            try:
                model_field = self.queryset.model._meta.get_field(name)
                if isinstance(model_field, (ManyToManyField, ManyToManyRel)):
                    m2m_fields[name] = model_field
                elif isinstance(model_field, GenericRel):
                    # Ignore generic relations (these may be used for other purposes in the form)
                    continue
                else:
                    model_fields[name] = model_field
            except FieldDoesNotExist:
                # This form field is used to modify a field rather than set its value directly
                # model_fields[name] = None
                pass

        for obj in self.queryset.filter(pk__in=form.cleaned_data['pk']):
            if obj.mapped_device_id is not None:
                continue

            extra = {'custom_field_data': {}}

            # Update standard fields. If a field is listed in _nullify, delete its value.
            for name, model_field in model_fields.items():
                # Handle nullification
                if name in form.nullable_fields and name in nullified_fields:
                    extra[name] = None if model_field.null else ''
                # Normal fields
                elif name in form.changed_data:
                    extra[name] = form.cleaned_data[name]
            # Update custom fields
            for name, customfield in custom_fields.items():
                assert name.startswith('cf_')
                cf_name = name[3:]  # Strip cf_ prefix
                if name in form.nullable_fields and name in nullified_fields:
                    extra[name]['custom_field_data'][cf_name] = None
                elif name in form.changed_data:
                    extra[name]['custom_field_data'][cf_name] = customfield.serialize(form.cleaned_data[name])

            device = get_dcim_device(obj, **extra)
            obj.mapped_device = device
            obj.save()

            log_message = f"Onboarded device - {obj.hostname} successfully."
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_SUCCESS, category=LogCategoryChoices.ONBOARD, message=log_message)

            # Take a snapshot of change-logged models
            if hasattr(device, 'snapshot'):
                device.snapshot()
            
            updated_objects.append(device)

            # Handle M2M fields after save
            for name, m2m_field in m2m_fields.items():
                if name in form.nullable_fields and name in nullified_fields:
                    getattr(device, name).clear()
                elif form.cleaned_data[name]:
                    getattr(device, name).set(form.cleaned_data[name])

            # Add/remove tags
            if form.cleaned_data.get('add_tags', None):
                device.tags.add(*form.cleaned_data['add_tags'])
            if form.cleaned_data.get('remove_tags', None):
                device.tags.remove(*form.cleaned_data['remove_tags'])

        return updated_objects


@method_decorator(slurpit_plugin_registered, name='dispatch')
class ImportDevices(View):
    def get(self, request, *args, **kwargs):
        try:
            result = run_import()
            if result == 'done':
                messages.info(request, "Synced the devices from Slurp'it.")
            else:
                pass
        except requests.exceptions.RequestException:
            messages.error(request, "An error occured during querying Slurp'it!")
            log_message = "An error occured during querying Slurp'it!"
            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.ONBOARD, message=log_message)
        return redirect(reverse('plugins:slurpit_netbox:importeddevice_list'))
    

