import django_filters
from core.choices import DataSourceStatusChoices
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet, BaseFilterSet
from .models import SlurpitLog, SlurpitPlanning, SlurpitSnapshot, SlurpitImportedDevice, SlurpitInitIPAddress, SlurpitInterface, SlurpitPrefix, SlurpitVLAN
from django.utils.translation import gettext as _
from utilities.filters import (
    ContentTypeFilter, MultiValueCharFilter
)
import netaddr
from netaddr.core import AddrFormatError

class LoggingFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    class Meta:
        model = SlurpitLog
        fields = [
            'log_time', 'level', 'category', 'message'
        ]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(level__icontains=value) | 
            Q(category__icontains=value) |
            Q(message__icontains=value)
        )

class SlurpitPlanningFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    class Meta:
        model = SlurpitPlanning
        fields = ["id", "name", "planning_id"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
        )
    
class SlurpitSnapshotFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    class Meta:
        model = SlurpitSnapshot
        fields = ["id", "hostname", "planning_id"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
        )

class SlurpitImportedDeviceFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    class Meta:
        model = SlurpitImportedDevice
        fields = ["id", "hostname", "device_os", "device_type", "fqdn", "brand", "ipv4"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(device_os__icontains=value) | 
            Q(hostname__icontains=value) | 
            Q(device_type__icontains=value) | 
            Q(fqdn__icontains=value) | 
            Q(brand__icontains=value) | 
            Q(ipv4__icontains=value)
        )

class SlurpitPrefixFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    prefix = MultiValueCharFilter(
        method='filter_prefix',
        label=_('Prefix'),
    )

    class Meta:
        model = SlurpitPrefix
        fields = ["id", "description", "prefix", "vrf"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = Q(description__icontains=value)
        qs_filter |= Q(prefix__contains=value.strip())
        qs_filter |= Q(vrf__name__contains=value)

        if value in 'Global':
            qs_filter |= Q(vrf=None)
        try:
            prefix = str(netaddr.IPNetwork(value.strip()).cidr)
            qs_filter |= Q(prefix__net_contains_or_equals=prefix)
            qs_filter |= Q(prefix__contains=value.strip())
        except (AddrFormatError, ValueError):
            pass
        return queryset.filter(qs_filter)


class SlurpitIPAddressFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    address = MultiValueCharFilter(
        method='filter_address',
        label=_('Address'),
    )

    class Meta:
        model = SlurpitInitIPAddress
        fields = [
            'address', 'dns_name', 'description'
        ] 

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        
        return queryset.filter(
            Q(dns_name__icontains=value) | 
            Q(description__icontains=value) | 
            Q(address__icontains=value)
        )
    
class SlurpitInterfaceFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    class Meta:
        model = SlurpitInterface
        fields = [
            'name', 'device', 'type', 'description'
        ] 

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        
        return queryset.filter(
            Q(name__icontains=value) | 
            Q(description__icontains=value) | 
            Q(type__icontains=value) | 
            Q(device__name__icontains=value)
        )
    
class SlurpitVLANFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    class Meta:
        model = SlurpitVLAN
        fields = [
            'name', 'description'
        ] 

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        
        return queryset.filter(
            Q(name__icontains=value) | 
            Q(description__icontains=value)
        )