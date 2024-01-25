import django_filters
from core.choices import DataSourceStatusChoices
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet, BaseFilterSet
from .models import SlurpitLog, SlurpitPlanning, SlurpitSnapshot, SlurpitImportedDevice
from django.utils.translation import gettext as _


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
        fields = ["id", "hostname"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
        )
