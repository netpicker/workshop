from netbox.views import generic

from ..models import SlurpitInitIPAddress, SlurpitLog
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

@method_decorator(slurpit_plugin_registered, name='dispatch')
class ReconcileView(generic.ObjectListView):
    queryset = models.SlurpitInitIPAddress.objects.exclude(address = None)
    table = tables.SlurpitIPAMTable
    template_name = "slurpit_netbox/reconcile.html"

    def post(self, request, **kwargs):
        pk_list = request.POST.getlist('pk')
        action = request.POST.get('action')

        if len(pk_list):
            if action == 'decline':
                try:
                    deline_items = SlurpitInitIPAddress.objects.filter(pk__in=pk_list).delete()
                    messages.info(request, "Declined the selected IP Addresses successfully .")
                except:
                    messages.warning(request, "Failed to decline IP Addresses.")
            else:
                reconcile_items =SlurpitInitIPAddress.objects.filter(pk__in=pk_list)
                
                batch_insert_qs = []
                batch_update_qs = []
                batch_insert_ids = []
                batch_update_ids = []

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
                log_message = "Failed to accept since no ip addresses were selected."
            else:
                log_message = "Failed to decline since no ip addresses were selected."

            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.RECONCILE, message=log_message)
            
        return redirect(reverse("plugins:slurpit_netbox:reconcile_list"))
    
class ReconcileDetailView(generic.ObjectView):
    queryset = models.SlurpitInitIPAddress.objects.all()

    template_name = 'slurpit_netbox/reconcile_detail.html'

    def get(self, request, pk, **kwargs):
        """
        GET handler for rendering child objects.
        """
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
                'ipaddress': ipaddress,
                'diff_added': diff_added,
                'diff_removed': diff_removed,
                'incomming_change': incomming_change,
                'current_state': current_state,
                'updated_time': updated_time,
                'action': action,
                'object_type': object_type
            },
        )