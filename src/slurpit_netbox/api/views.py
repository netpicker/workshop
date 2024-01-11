
from netbox.api.viewsets import NetBoxModelViewSet
from slurpit_netbox.models import SlurpitPlan
from slurpit_netbox.filtersets import SlurpitPlanFilterSet
from .serializers import SlurpitPlanSerializer
from rest_framework.routers import APIRootView

__all__ = (
    'SlurpitPlanViewSet',
    'SlurpitRootView',
)

class SlurpitRootView(APIRootView):
    """
    Slurpit API root view
    """
    def get_view_name(self):
        return 'Slurpit'
    
#
# Viewsets
#
class SlurpitPlanViewSet(NetBoxModelViewSet):
    queryset = SlurpitPlan.objects.all()
    serializer_class = SlurpitPlanSerializer
    filterset_class = SlurpitPlanFilterSet