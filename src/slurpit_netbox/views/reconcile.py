from netbox.views import generic
from django.http import JsonResponse

from ..models import SlurpitInitIPAddress, SlurpitLog, SlurpitInterface, SlurpitPrefix
from .. import forms, importer, models, tables
from ..decorators import slurpit_plugin_registered
from django.utils.decorators import method_decorator
from django.shortcuts import render
from ipam.models import FHRPGroup, VRF, IPAddress, Prefix
from utilities.data import shallow_compare_dict
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from ..management.choices import *
from ..importer import BATCH_SIZE
from django.db import transaction
from dcim.models import Interface
from urllib.parse import urlencode
from ..filtersets import SlurpitIPAddressFilterSet, SlurpitInterfaceFilterSet, SlurpitPrefixFilterSet
from utilities.views import register_model_view
from ..forms import SlurpitPrefixForm, SlurpitDeviceInterfaceForm, SlurpitInitIPAMForm

class SlurpitInitIPAddressListView(generic.ObjectListView):
    queryset = SlurpitInitIPAddress.objects.all()
    table = tables.SlurpitIPAMTable

class SlurpitPrefixListView(generic.ObjectListView):
    queryset = SlurpitPrefix.objects.all()
    table = tables.SlurpitPrefixTable

class SlurpitInterfaceListView(generic.ObjectListView):
    queryset = SlurpitInterface.objects.all()
    table = tables.SlurpitInterfaceTable
    
@method_decorator(slurpit_plugin_registered, name='dispatch')
class ReconcileView(generic.ObjectListView):
    queryset = models.SlurpitInitIPAddress.objects.exclude(address = None)
    table = tables.SlurpitIPAMTable
    template_name = "slurpit_netbox/reconcile.html"
    filterset = SlurpitIPAddressFilterSet
    # action_buttons = []

    def get(self, request, *args, **kwargs):
        
        tab = request.GET.get('tab')
        if tab == None or tab == 'ipam':
            pass
        elif tab == 'prefix':
            self.queryset = models.SlurpitPrefix.objects.exclude(prefix = None)
            self.table = tables.SlurpitPrefixTable
            self.filterset = SlurpitPrefixFilterSet
        else:
            self.queryset = models.SlurpitInterface.objects.exclude(name = '')
            self.table = tables.SlurpitInterfaceTable
            self.filterset = SlurpitInterfaceFilterSet

        return super().get(request, *args, **kwargs)
    
    def get_extra_context(self, request, *args, **kwargs):
        reconcile_type = request.GET.get('tab')
        pk = request.GET.get('pk')
        return_values = {}
        """
        GET handler for rendering child objects.
        """
        title = ""

        if pk:
            if reconcile_type == 'interface':
                self.queryset = models.SlurpitInterface.objects.all()
                # instance = models.SlurpitInterface.object.get(pk=pk, **kwargs)
                diff_added = None
                diff_removed = None
                action = 'Updated'
                

                interface_fields = ['name', 'label','description', 'device', 'module', 'type', 'duplex', 'speed']

                incomming_queryset = SlurpitInterface.objects.filter(pk=pk)
                incomming_obj = incomming_queryset.values(*interface_fields).first()

                name = str(incomming_queryset.first().name)
                updated_time = incomming_queryset.first().last_updated
                title = name
                device = incomming_obj['device']
                incomming_obj['device'] = device

                incomming_change = {**incomming_obj}

                current_queryset = Interface.objects.filter(name=name, device=device)

                if current_queryset:
                    current_obj = current_queryset.values(*interface_fields).first()
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
            
            elif reconcile_type == 'prefix':
                self.queryset = models.SlurpitPrefix.objects.all()
                # instance = models.SlurpitPrefix.objects.get(pk=pk, **kwargs)
                diff_added = None
                diff_removed = None
                action = 'Updated'
                
                prefix_fields = ['prefix', 'status','vrf', 'vlan', 'tenant', 'site', 'role', 'description']

                incomming_queryset = SlurpitPrefix.objects.filter(pk=pk)
                incomming_change = incomming_queryset.values(*prefix_fields).first()
                incomming_change['prefix'] = str(incomming_change['prefix'])

                prefix = str(incomming_queryset.first().prefix)
                updated_time = incomming_queryset.first().last_updated
                title = prefix
                vrf = None

                if incomming_change['vrf'] is not None:
                    vrf = VRF.objects.get(pk=incomming_change['vrf'])
                current_queryset = Prefix.objects.filter(prefix=prefix, vrf=vrf)

                if current_queryset:
                    current_obj = current_queryset.values(*prefix_fields).first()
                    current_state = {**current_obj}
                    current_state['prefix'] = str(current_state['prefix'])
                    
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


                object_type = f'{Prefix._meta.app_label} | {Prefix._meta.verbose_name}'

            else:
                # instance = models.SlurpitInitIPAddress.objects.get(pk=pk, **kwargs)
                diff_added = None
                diff_removed = None
                action = 'Updated'

                ipam_fields = ['address', 'status', 'dns_name', 'description', 'vrf', 'tenant', 'role']

                incomming_queryset = SlurpitInitIPAddress.objects.filter(pk=pk)
                incomming_obj = incomming_queryset.values(*ipam_fields).first()

                ipaddress = str(incomming_queryset.first().address)
                updated_time = incomming_queryset.first().last_updated


                title = ipaddress
                vrf = incomming_obj['vrf']
                
                incomming_obj['address'] = ipaddress
                incomming_change = {**incomming_obj}

                

                current_queryset = IPAddress.objects.filter(address=ipaddress, vrf=vrf)
                if current_queryset:
                    current_obj = current_queryset.values(*ipam_fields).first()
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

            return_values = {
                'object': instance,
                'title': title,
                'diff_added': diff_added,
                'diff_removed': diff_removed,
                'incomming_change': incomming_change,
                'current_state': current_state,
                'updated_time': updated_time,
                'action': action,
                'object_type': object_type
            }

        if reconcile_type == 'interface':
            edit_bulk_url = reverse("plugins:slurpit_netbox:slurpitinterface_bulk_edit")
        elif reconcile_type == 'prefix':
            edit_bulk_url = reverse("plugins:slurpit_netbox:slurpitprefix_bulk_edit")
        else:
            edit_bulk_url = reverse("plugins:slurpit_netbox:slurpitipaddress_bulk_edit")
        return_values = {
            **return_values,
            'ipam_count': models.SlurpitInitIPAddress.objects.exclude(address = None).count(),
            'interface_count': models.SlurpitInterface.objects.exclude(name = '').count(),
            'prefix_count': models.SlurpitPrefix.objects.exclude(prefix = None).count(),
            'edit_bulk_url': edit_bulk_url
        }

        return return_values
    
    def post(self, request, **kwargs):
        pk_list = request.POST.getlist('pk')
        action = request.POST.get('action')
        tab = request.POST.get('tab')
        _all = request.POST.get('_all')

        if action == 'get':
            pk = request.POST.get('pk')

            if tab == 'interface':
                self.queryset = models.SlurpitInterface.objects.all()
                # instance = models.SlurpitInterface.object.get(pk=pk, **kwargs)
                diff_added = None
                diff_removed = None
                action = 'Updated'
                

                interface_fields = ['name', 'label','description', 'device', 'module', 'type', 'duplex', 'speed']

                incomming_queryset = SlurpitInterface.objects.filter(pk=pk)
                incomming_obj = incomming_queryset.values(*interface_fields).first()

                name = str(incomming_queryset.first().name)
                updated_time = incomming_queryset.first().last_updated
                title = name
                device = incomming_obj['device']
                incomming_obj['device'] = device

                incomming_change = {**incomming_obj}

                current_queryset = Interface.objects.filter(name=name, device=device)

                if current_queryset:
                    current_obj = current_queryset.values(*interface_fields).first()
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
            
            elif tab == 'prefix':
                self.queryset = models.SlurpitPrefix.objects.all()
                # instance = models.SlurpitPrefix.objects.get(pk=pk, **kwargs)
                diff_added = None
                diff_removed = None
                action = 'Updated'
                
                prefix_fields = ['prefix', 'status','vrf', 'vlan', 'tenant', 'site', 'role', 'description']

                incomming_queryset = SlurpitPrefix.objects.filter(pk=pk)
                incomming_change = incomming_queryset.values(*prefix_fields).first()
                incomming_change['prefix'] = str(incomming_change['prefix'])

                prefix = str(incomming_queryset.first().prefix)
                updated_time = incomming_queryset.first().last_updated
                title = prefix
                vrf = None

                if incomming_change['vrf'] is not None:
                    vrf = VRF.objects.get(pk=incomming_change['vrf'])
                current_queryset = Prefix.objects.filter(prefix=prefix, vrf=vrf)

                if current_queryset:
                    current_obj = current_queryset.values(*prefix_fields).first()
                    current_state = {**current_obj}
                    current_state['prefix'] = str(current_state['prefix'])
                    
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


                object_type = f'{Prefix._meta.app_label} | {Prefix._meta.verbose_name}'

            else:
                # instance = models.SlurpitInitIPAddress.objects.get(pk=pk, **kwargs)
                diff_added = None
                diff_removed = None
                action = 'Updated'

                ipam_fields = ['address', 'status', 'dns_name', 'description', 'vrf', 'tenant', 'role']

                incomming_queryset = SlurpitInitIPAddress.objects.filter(pk=pk)
                incomming_obj = incomming_queryset.values(*ipam_fields).first()

                ipaddress = str(incomming_queryset.first().address)
                updated_time = incomming_queryset.first().last_updated


                title = ipaddress
                vrf = incomming_obj['vrf']
                
                incomming_obj['address'] = ipaddress
                incomming_change = {**incomming_obj}

                

                current_queryset = IPAddress.objects.filter(address=ipaddress, vrf=vrf)
                if current_queryset:
                    current_obj = current_queryset.values(*ipam_fields).first()
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

            return_values = {
                'title': title,
                'diff_added': diff_added,
                'diff_removed': diff_removed,
                'incomming_change': incomming_change,
                'current_state': current_state,
                'updated_time': updated_time,
                'action': action,
                'object_type': object_type
            }

            return JsonResponse(return_values)
        
        if _all or len(pk_list):
            if action == 'decline':
                try:
                    if tab == 'interface':
                        if _all:
                            deline_items = models.SlurpitInterface.objects.exclude(name='').delete()
                        else:
                            deline_items = models.SlurpitInterface.objects.filter(pk__in=pk_list).delete()

                        messages.info(request, "Declined the selected Interfaces successfully .")
                    elif tab == 'prefix':
                        if _all:
                            deline_items = models.SlurpitPrefix.objects.exclude(prefix=None).delete()
                        else:
                            deline_items = models.SlurpitPrefix.objects.filter(pk__in=pk_list).delete()
                        messages.info(request, "Declined the selected Prefixes successfully .")
                    else:
                        if _all:
                            deline_items = SlurpitInitIPAddress.objects.exclude(address=None).delete()
                        else:
                            deline_items = SlurpitInitIPAddress.objects.filter(pk__in=pk_list).delete()
                        messages.info(request, "Declined the selected IP Addresses successfully .")
                except:
                    if tab == 'interface':
                        messages.warning(request, "Failed to decline Interfaces.")
                    elif tab == 'prefix':
                        messages.warning(request, "Failed to decline Prefixes.")
                    else:
                        messages.warning(request, "Failed to decline IP Addresses.")
            else:
                batch_insert_qs = []
                batch_update_qs = []
                batch_insert_ids = []
                batch_update_ids = []

                if tab == 'interface':
                    if _all:
                        reconcile_items = SlurpitInterface.objects.exclude(name='')
                    else:
                        reconcile_items = SlurpitInterface.objects.filter(pk__in=pk_list)

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
                                    name = item.name,
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
                elif tab == 'prefix':
                    if _all:
                        reconcile_items =SlurpitPrefix.objects.exclude(prefix=None)
                    else:
                        reconcile_items =SlurpitPrefix.objects.filter(pk__in=pk_list)
                    for item in reconcile_items:
                        netbox_prefix = Prefix.objects.filter(prefix=item.prefix, vrf=item.vrf)
                        # If the prefix is existed in netbox
                        if netbox_prefix:
                            netbox_prefix = netbox_prefix.first()

                            if item.status:
                                netbox_prefix.status = item.status
                            if item.description:
                                netbox_prefix.description = item.description
                            else:
                                netbox_prefix.description = ""
                                
                            if item.tenant:
                                netbox_prefix.tenant = item.tenant
                            if item.role:
                                netbox_prefix.role = item.role
                            if item.vlan:
                                netbox_prefix.vlan = item.vlan
                            if item.site:
                                netbox_prefix.site = item.site

                            batch_update_qs.append(netbox_prefix)
                            batch_update_ids.append(item.pk)
                        else:
                            batch_insert_qs.append(
                                Prefix(
                                    prefix = item.prefix,
                                    status = item.status, 
                                    vrf = item.vrf,
                                    role = item. role, 
                                    vlan = item.vlan,
                                    description = item.description,
                                    tenant = item.tenant,
                                    site = item.site
                            ))
                            batch_insert_ids.append(item.pk)
                        
                    count = len(batch_insert_qs)
                    offset = 0
                    while offset < count:
                        batch_qs = batch_insert_qs[offset:offset + BATCH_SIZE]
                        batch_ids = batch_insert_ids[offset:offset + BATCH_SIZE]
                        to_import = []        
                        for prefix_item in batch_qs:
                            to_import.append(prefix_item)

                        with transaction.atomic():
                            Prefix.objects.bulk_create(to_import)
                            SlurpitPrefix.objects.filter(pk__in=batch_ids).delete()
                        offset += BATCH_SIZE

                    count = len(batch_update_qs)
                    offset = 0
                    while offset < count:
                        batch_qs = batch_update_qs[offset:offset + BATCH_SIZE]
                        batch_ids = batch_update_ids[offset:offset + BATCH_SIZE]
                        to_import = []        
                        for prefix_item in batch_qs:
                            to_import.append(prefix_item)

                        with transaction.atomic():
                            Prefix.objects.bulk_update(to_import, fields={'status', 'vrf', 'role', 'site', 'vlan', 'tenant', 'description'})
                        
                            SlurpitPrefix.objects.filter(pk__in=batch_ids).delete()

                        offset += BATCH_SIZE
                else:
                    if _all:
                        reconcile_items =SlurpitInitIPAddress.objects.exclude(address=None)
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
                            else:
                                netbox_ipaddress.dns_name = ""

                            if item.description:
                                netbox_ipaddress.description = item.description
                            else:
                                netbox_ipaddress.description = ""

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
                                    dns_name = item.dns_name,
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
            messages.warning(request, "No Reconcile Items were selected.")

            if action == 'accept':
                if tab == 'interface':
                    log_message = "Failed to accept since no ip addresses were selected."
                elif tab == 'prefix':
                    log_message = "Failed to accept since no prefixes were selected."
                else:
                    log_message = "Failed to accept since no interfaces were selected."
            else:
                if tab == 'interface':
                    log_message = "Failed to decline since no ip addresses were selected."
                elif tab == 'prefix':
                    log_message = "Failed to decline since no prefixes were selected."
                
                else:
                    log_message = "Failed to decline since no interfaces were selected."

            SlurpitLog.objects.create(level=LogLevelChoices.LOG_FAILURE, category=LogCategoryChoices.RECONCILE, message=log_message)
        
        if tab is None:
            tab = 'ipam'
        query_params = {'tab': tab}
        base_url = reverse("plugins:slurpit_netbox:reconcile_list")
        # Encode your query parameters and append them to the base URL
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        return redirect(url_with_querystring)
    
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
            

            interface_fields = ['name', 'label','description', 'device', 'module', 'type', 'duplex', 'speed']

            incomming_queryset = SlurpitInterface.objects.filter(pk=pk)
            incomming_obj = incomming_queryset.values(*interface_fields).first()

            name = str(incomming_queryset.first().name)
            updated_time = incomming_queryset.first().last_updated
            title = name
            device = incomming_obj['device']
            incomming_obj['device'] = device

            incomming_change = {**incomming_obj}

            current_queryset = Interface.objects.filter(name=name, device=device)

            if current_queryset:
                current_obj = current_queryset.values(*interface_fields).first()
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
        
        elif reconcile_type == 'prefix':
            self.queryset = models.SlurpitPrefix.objects.all()
            instance = self.get_object(pk=pk, **kwargs)
            diff_added = None
            diff_removed = None
            action = 'Updated'
            
            prefix_fields = ['prefix', 'status','vrf', 'vlan', 'tenant', 'site', 'role', 'description']

            incomming_queryset = SlurpitPrefix.objects.filter(pk=pk)
            incomming_change = incomming_queryset.values(*prefix_fields).first()
            incomming_change['prefix'] = str(incomming_change['prefix'])

            prefix = str(incomming_queryset.first().prefix)
            updated_time = incomming_queryset.first().last_updated
            title = prefix
            vrf = None

            if incomming_change['vrf'] is not None:
                vrf = VRF.objects.get(pk=incomming_change['vrf'])
            current_queryset = Prefix.objects.filter(prefix=prefix, vrf=vrf)

            if current_queryset:
                current_obj = current_queryset.values(*prefix_fields).first()
                current_state = {**current_obj}
                current_state['prefix'] = str(current_state['prefix'])
                
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


            object_type = f'{Prefix._meta.app_label} | {Prefix._meta.verbose_name}'

        else:
            instance = self.get_object(pk=pk, **kwargs)
            diff_added = None
            diff_removed = None
            action = 'Updated'

            ipam_fields = ['address', 'status', 'dns_name', 'description', 'vrf', 'tenant', 'role']

            incomming_queryset = SlurpitInitIPAddress.objects.filter(pk=pk)
            incomming_obj = incomming_queryset.values(*ipam_fields).first()

            ipaddress = str(incomming_queryset.first().address)
            updated_time = incomming_queryset.first().last_updated


            title = ipaddress
            vrf = incomming_obj['vrf']
            
            incomming_obj['address'] = ipaddress
            incomming_change = {**incomming_obj}

            current_queryset = IPAddress.objects.filter(address=ipaddress, vrf=vrf)
            if current_queryset:
                current_obj = current_queryset.values(*ipam_fields).first()
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
                'object_action': instance.action,
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
    
class SlurpitPrefixEditView(generic.ObjectEditView):
    queryset = SlurpitPrefix.objects.all()
    form = SlurpitPrefixForm
    template_name = 'slurpit_netbox/object_edit.html'

class SlurpitInterfaceEditView(generic.ObjectEditView):
    queryset = SlurpitInterface.objects.all()
    form = forms.SlurpitDeviceInterfaceEditForm
    template_name = 'slurpit_netbox/object_edit.html'

class SlurpitIPAddressEditView(generic.ObjectEditView):
    queryset = SlurpitInitIPAddress.objects.all()
    form = forms.SlurpitInitIPAMEditForm
    template_name = 'slurpit_netbox/object_edit.html'

class SlurpitInterfaceBulkEditView(generic.BulkEditView):
    queryset = SlurpitInterface.objects.all()
    filterset = SlurpitInterfaceFilterSet
    table = tables.SlurpitInterfaceTable
    form = forms.SlurpitInterfaceBulkEditForm
    template_name = 'slurpit_netbox/object_bulkedit.html'
class SlurpitPrefixBulkEditView(generic.BulkEditView):
    queryset = SlurpitPrefix.objects.all()
    filterset = SlurpitPrefixFilterSet
    table = tables.SlurpitPrefixTable
    form = forms.SlurpitPrefixBulkEditForm
    template_name = 'slurpit_netbox/object_bulkedit.html'
class SlurpitIPAddressBulkEditView(generic.BulkEditView):
    queryset = SlurpitInitIPAddress.objects.all()
    filterset = SlurpitIPAddressFilterSet
    table = tables.SlurpitIPAMTable
    form = forms.SlurpitIPAddressBulkEditForm
    template_name = 'slurpit_netbox/object_bulkedit.html'