import logging

from django.contrib import messages
from django.contrib.contenttypes.fields import GenericRel
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import ManyToManyField, ManyToManyRel
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from extras.signals import clear_webhooks
from netbox.views import generic
from utilities.exceptions import AbortRequest, PermissionsViolation
from utilities.forms import restrict_form_fields

# from . import filtersets, forms, models, tables
from . import forms, importer, models, tables
from .importer import get_dcim, import_from_queryset, run_import


class ImportedDeviceListView(generic.ObjectListView):
    queryset = models.ImportedDevice.objects
    table = tables.ImportedDeviceTable
    template_name = "slurpit_netbox/importeddevice_list.html"

    def post(self, request):
        pks = map(int, request.POST.getlist('pk'))
        qs = self.queryset.filter(pk__in=pks, mapped_device_id__isnull=True)
        import_from_queryset(qs)
        return redirect(request.path)


class ImportedDeviceOnboardView(generic.BulkEditView):
    template_name = 'slurpit_netbox/bulk_edit.html'
    queryset = models.ImportedDevice.objects.all()
    table = tables.ImportedDeviceTable
    model_form = forms.OnboardingForm
    form = forms.OnboardingForm

    def post(self, request, **kwargs):
        logger = logging.getLogger(__name__)
        model = self.queryset.model

        # If we are editing *all* objects in the queryset, replace the PK list with all matched objects.
        if request.POST.get('_all') and self.filterset is not None:
            pk_list = self.filterset(request.GET, self.queryset.values_list('pk', flat=True), request=request).qs
        else:
            pk_list = request.POST.getlist('pk')

        # Include the PK list as initial data for the form
        initial_data = {'pk': pk_list}

        # Check for other contextual data needed for the form. We avoid passing all of request.GET because the
        # filter values will conflict with the bulk edit form fields.
        # TODO: Find a better way to accomplish this
        if 'device' in request.GET:
            initial_data['device'] = request.GET.get('device')
        elif 'device_type' in request.GET:
            initial_data['device_type'] = request.GET.get('device_type')
        elif 'virtual_machine' in request.GET:
            initial_data['virtual_machine'] = request.GET.get('virtual_machine')

        if '_apply' in request.POST:
            form = self.form(request.POST, initial=initial_data)
            restrict_form_fields(form, request.user)

            if form.is_valid():
                logger.debug("Form validation was successful")
                try:
                    with transaction.atomic():
                        updated_objects = self._update_objects(form, request)

                        # Enforce object-level permissions
                        object_count = self.queryset.filter(pk__in=[obj.pk for obj in updated_objects]).count()
                        if object_count != len(updated_objects):
                            raise PermissionsViolation

                    if updated_objects:
                        msg = f'Onboarded {len(updated_objects)} {model._meta.verbose_name_plural}'
                        logger.info(msg)
                        messages.success(self.request, msg)

                    return redirect(self.get_return_url(request))

                except ValidationError as e:
                    messages.error(self.request, ", ".join(e.messages))
                    clear_webhooks.send(sender=self)

                except (AbortRequest, PermissionsViolation) as e:
                    logger.debug(e.message)
                    form.add_error(None, e.message)
                    clear_webhooks.send(sender=self)

            else:
                logger.debug("Form validation failed")

        else:
            defaults = importer.get_defaults()
            for k, v in defaults.items():
                initial_data.setdefault(k, str(v.id))
            form = self.form(initial=initial_data)
            restrict_form_fields(form, request.user)

        # Retrieve objects being edited
        table = self.table(self.queryset.filter(pk__in=pk_list, mapped_device_id__isnull=True), orderable=False)
        if not table.rows:
            messages.warning(request, "No onboardable {} were selected.".format(model._meta.verbose_name_plural))
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

            device = get_dcim(obj, **extra)
            obj.mapped_device = device
            obj.save()
            
            # Take a snapshot of change-logged models
            if hasattr(device, 'snapshot'):
                device.snapshot()

            # device.full_clean()
            # device.save()
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


class ImportDevices(View):
    def get(self, request, *args, **kwargs):
        run_import()
        return redirect(reverse('plugins:slurpit_netbox:importeddevice_list'))
