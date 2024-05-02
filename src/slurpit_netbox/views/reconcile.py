from netbox.views import generic

from ..models import SlurpitInitIPAddress, SlurpitLog, SlurpitInterface
from .. import forms, importer, models, tables
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from django.shortcuts import render
from ipam.models import FHRPGroup, VRF, IPAddress
from utilities.utils import shallow_compare_dict
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from ..management.choices import *
from ..importer import BATCH_SIZE
from django.db import transaction
from dcim.models import Interface

@method_decorator(slurpit_plugin_registered, name='dispatch')
class ReconcileView(generic.ObjectListView):
    queryset = models.SlurpitInitIPAddress.objects.exclude(address = None)
    table = tables.SlurpitIPAMTable
    template_name = "slurpit_netbox/reconcile.html"

    def get(self, request, *args, **kwargs):
        
        tab = request.GET.get('tab')
        if tab == None or tab == 'ipam':
            pass
        else:
            self.queryset = models.SlurpitInterface.objects.exclude(name = '')
            self.table = tables.SlurpitInterfaceTable

        return super().get(request, *args, **kwargs)
    
    def post(self, request, **kwargs):
        pk_list = request.POST.getlist('pk')
        action = request.POST.get('action')
        tab = request.POST.get('tab')

        if len(pk_list):
            if action == 'decline':
                try:
                    if tab == 'interface':
                        deline_items = models.SlurpitInterface.objects.filter(pk__in=pk_list).delete()
                        messages.info(request, "Declined the selected Interfaces successfully .")
                    else:
                        deline_items = SlurpitInitIPAddress.objects.filter(pk__in=pk_list).delete()
                        messages.info(request, "Declined the selected IP Addresses successfully .")
                except:
                    if tab == 'interface':
                        messages.warning(request, "Failed to decline Interfaces.")
                    else:
                        messages.warning(request, "Failed to decline IP Addresses.")
            else:
                batch_insert_qs = []
                batch_update_qs = []
                batch_insert_ids = []
                batch_update_ids = []

                if tab == 'interface':
                    reconcile_items =SlurpitInterface.objects.filter(pk__in=pk_list)

                    for item in reconcile_items:
                        netbox_interface = Interface.objects.filter(name=item.name, device=item.device)
                        # If the interface is existed in netbox
                        if netbox_interface:
                            netbox_interface = netbox_interface.first()

                            if item.label:
                                netbox_interface.label = item.label
                            if item.speed:
                                netbox_interface.speed = item.speed
                            if item.description:
                                netbox_interface.description = item.description

                            if item.type:
                                netbox_interface.type = item.type
                            if item.duplex:
                                netbox_interface.duplex = item.duplex
                            if item.module:
                                netbox_interface.module = item.module


                            batch_update_qs.append(netbox_interface)
                            batch_update_ids.append(item.pk)
                        else:
                            batch_insert_qs.append(
                                Interface(
                                    label = item.label, 
                                    device = item.device,
                                    speed = item. speed, 
                                    type = item.type,
                                    description = item.description,
                                    duplex = item.duplex,
                                    module = item.module
                            ))
                            batch_insert_ids.append(item.pk)
                        
                    count = len(batch_insert_qs)
                    offset = 0
                    while offset < count:
                        batch_qs = batch_insert_qs[offset:offset + BATCH_SIZE]
                        batch_ids = batch_insert_ids[offset:offset + BATCH_SIZE]
                        to_import = []        
                        for interface_item in batch_qs:
                            to_import.append(interface_item)

                        with transaction.atomic():
                            Interface.objects.bulk_create(to_import)
                            SlurpitInterface.objects.filter(pk__in=batch_ids).delete()
                        offset += BATCH_SIZE

                    count = len(batch_update_qs)
                    offset = 0
                    while offset < count:
                        batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                        batch_ids = batch_update_ids[offset:offset + BATCH_SIZE]
                        to_import = []        
                        for interface_item in batch_qs:
                            to_import.append(interface_item)

                        with transaction.atomic():
                            Interface.objects.bulk_update(to_import, fields={'label', 'speed', 'type', 'duplex', 'description', 'module'})
                        
                            SlurpitInterface.objects.filter(pk__in=batch_ids).delete()

                        offset += BATCH_SIZE
                else:
                    reconcile_items =SlurpitInitIPAddress.objects.filter(pk__in=pk_list)

                    for item in reconcile_items:
                        netbox_ipaddress = IPAddress.objects.filter(address=item.address, vrf=item.vrf)
                        # If the ip address is existed in netbox
                        if netbox_ipaddress:
                            netbox_ipaddress = netbox_ipaddress.first()
                            netbox_ipaddress.status = item.status
                            netbox_ipaddress.role = item.role
                            netbox_ipaddress.tennat = item.tenant

                            if item.dns_name:
                                netbox_ipaddress.dns_name = item.dns_name
                            if item.description:
                                netbox_ipaddress.description = item.description

                            batch_update_qs.append(netbox_ipaddress)
                            batch_update_ids.append(item.pk)
                        else:
                            batch_insert_qs.append(
                                IPAddress(
                                    address = item.address, 
                                    vrf = item.vrf,
                                    status = item. status, 
                                    role = item.role,
                                    description = item.description,
                                    tenant = item.tenant,
                                    dns_name = item.dns_name
                            ))
                            batch_insert_ids.append(item.pk)
                        
                    count = len(batch_insert_qs)
                    offset = 0
                    while offset < count:
                        batch_qs = batch_insert_qs[offset:offset + BATCH_SIZE]
                        batch_ids = batch_insert_ids[offset:offset + BATCH_SIZE]
                        to_import = []        
                        for ipaddress_item in batch_qs:
                            to_import.append(ipaddress_item)

                        with transaction.atomic():
                            IPAddress.objects.bulk_create(to_import)
                            SlurpitInitIPAddress.objects.filter(pk__in=batch_ids).delete()
                        offset += BATCH_SIZE

                    count = len(batch_update_qs)
                    offset = 0
                    while offset < count:
                        batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                        batch_ids = batch_update_ids[offset:offset + BATCH_SIZE]
                        to_import = []        
                        for ipaddress_item in batch_qs:
                            to_import.append(ipaddress_item)

                        with transaction.atomic():
                            IPAddress.objects.bulk_update(to_import, fields={'status', 'role', 'tenant', 'dns_name', 'description'})
                        
                            SlurpitInitIPAddress.objects.filter(pk__in=batch_ids).delete()

                        offset += BATCH_SIZE
        else:
            messages.warning(request, "No IP Addresses were selected.")

            if action == 'accept':
                if tab == 'interface':
                    log_message = "Failed to accept since no ip addresses were selected."
                else:
                    log_message = "Failed to accept since no interfaces were selected."
            else:
                if tab == 'interface':
                    log_message = "Failed to decline since no ip addresses were selected."
                else:
                    log_message = "Failed to decline since no interfaces were selected."

            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.RECONCILE, message=log_message)
            
        return redirect(reverse("plugins:slurpit_netbox:reconcile_list"))
    
class ReconcileDetailView(generic.ObjectView):
    queryset = models.SlurpitInitIPAddress.objects.all()

    template_name = 'slurpit_netbox/reconcile_detail.html'

    def get(self, request, pk, reconcile_type, **kwargs):
        """
        GET handler for rendering child objects.
        """
        title = ""
        if reconcile_type == 'interface':
            self.queryset = models.SlurpitInterface.objects.all()
            instance = self.get_object(pk=pk, **kwargs)
            diff_added = None
            diff_removed = None
            action = 'Updated'
            

            interface_initial_fields = ['device', 'module', 'type', 'tags', 'duplex', 'speed']
            interface_fields = ['name', 'label','description']
            initial_obj = SlurpitInterface.objects.filter(name='').values(*interface_initial_fields).first()
            incomming_queryset = SlurpitInterface.objects.filter(pk=pk)
            incomming_obj = incomming_queryset.values(*interface_fields).first()

            name = str(incomming_queryset.first().name)
            updated_time = incomming_queryset.first().last_updated
            title = name
            device = initial_obj['device']
            incomming_obj['device'] = device

            incomming_change = {**initial_obj, **incomming_obj}

            current_queryset = Interface.objects.filter(name=name, device=device)

            if current_queryset:
                current_obj = current_queryset.values(*interface_initial_fields, *interface_fields).first()
                current_obj['name'] = name
                current_state = {**current_obj}
                instance = current_queryset.first()
            else:
                current_state = None
                instance = None
                action = 'Created'
            

            if current_state and incomming_change:
                diff_added = shallow_compare_dict(
                    current_state or dict(),
                    incomming_change or dict(),
                    exclude=['last_updated'],
                )
                diff_removed = {
                    x: current_state.get(x) for x in diff_added
                } if current_state else {}
            else:
                diff_added = None
                diff_removed = None

            object_type = f'{Interface._meta.app_label} | {Interface._meta.verbose_name}'
        
        else:
            instance = self.get_object(pk=pk, **kwargs)
            diff_added = None
            diff_removed = None
            action = 'Updated'
            

            ipam_initial_fields = ['status', 'vrf', 'tenant', 'tags', 'role']
            ipam_fields = ['address', 'status', 'dns_name', 'description']
            initial_obj = SlurpitInitIPAddress.objects.filter(address=None).values(*ipam_initial_fields).first()
            incomming_queryset = SlurpitInitIPAddress.objects.filter(pk=pk)
            incomming_obj = incomming_queryset.values(*ipam_fields).first()

            ipaddress = str(incomming_queryset.first().address)
            updated_time = incomming_queryset.first().last_updated
            
            title = ipaddress
            vrf = initial_obj['vrf']
            incomming_obj['address'] = ipaddress
            incomming_change = {**initial_obj, **incomming_obj}

            current_queryset = IPAddress.objects.filter(address=ipaddress, vrf=vrf)
            if current_queryset:
                current_obj = current_queryset.values(*ipam_initial_fields, *ipam_fields).first()
                current_obj['address'] = ipaddress
                current_state = {**current_obj}
                instance = current_queryset.first()
            else:
                current_state = None
                instance = None
                action = 'Created'
            

            if current_state and incomming_change:
                diff_added = shallow_compare_dict(
                    current_state or dict(),
                    incomming_change or dict(),
                    exclude=['last_updated'],
                )
                diff_removed = {
                    x: current_state.get(x) for x in diff_added
                } if current_state else {}
            else:
                diff_added = None
                diff_removed = None

            object_type = f'{IPAddress._meta.app_label} | {IPAddress._meta.verbose_name}'

        return render(
            request,
            self.template_name,
            
            {
                'object': instance,
                'title': title,
                'diff_added': diff_added,
                'diff_removed': diff_removed,
                'incomming_change': incomming_change,
                'current_state': current_state,
                'updated_time': updated_time,
                'action': action,
                'object_type': object_type
            },
        )