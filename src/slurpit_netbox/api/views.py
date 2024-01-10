
from netbox.api.viewsets import NetBoxModelViewSet
from slurpit_netbox.models import SlurpitPlan
from slurpit_netbox.filtersets import SlurpitPlanFilterSet
from .serializers import SlurpitPlanSerializer

class SlurpitPlanViewSet(NetBoxModelViewSet):
    queryset = SlurpitPlan.objects.all()
    serializer_class = SlurpitPlanSerializer
    # filterset_class = SlurpitPlanFilterSet