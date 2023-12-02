import django_filters
from core.choices import DataSourceStatusChoices
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from .models import Source


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


