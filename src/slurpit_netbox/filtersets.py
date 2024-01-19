import django_filters
from core.choices import DataSourceStatusChoices
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet, BaseFilterSet
from .models import Source, SlurpitLog, SlurpitPlan, SlurpitDevice
from django.utils.translation import gettext as _

class SourceFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(
        choices=DataSourceStatusChoices, null_value=None
    )

    class Meta:
        model = Source
        fields = ("id", "name")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )

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

class SlurpitPlanFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    class Meta:
        model = SlurpitPlan
        fields = ["id", "name", "plan_id"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
        )
    
class SlurpitDeviceFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label=_('Search'),
    )

    class Meta:
        model = SlurpitDevice
        fields = ["id", "hostname", "plan_id"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
        )

