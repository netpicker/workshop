
from netbox.api.viewsets import NetBoxModelViewSet
from slurpit_netbox.models import SlurpitPlan, SlurpitDevice
from slurpit_netbox.filtersets import SlurpitPlanFilterSet, SlurpitDeviceFilterSet
from .serializers import SlurpitPlanSerializer, SlurpitDeviceSerializer
from rest_framework.routers import APIRootView
from rest_framework_bulk import BulkCreateModelMixin, BulkDestroyModelMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

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
class SlurpitPlanViewSet(
        BulkCreateModelMixin,
        BulkDestroyModelMixin,
        NetBoxModelViewSet
    ):
    queryset = SlurpitPlan.objects.all()
    serializer_class = SlurpitPlanSerializer
    filterset_class = SlurpitPlanFilterSet

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request, *args, **kwargs):
        """
        A custom action to delete all SlurpitPlan objects.
        Be careful with this operation: it cannot be undone!
        """
        # Perform the deletion and return a response
        self.queryset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def get_queryset(self):
        if self.request.method == 'GET':
            # Customize this queryset to suit your requirements for GET requests
            return SlurpitPlan.objects.filter(selected=True)
        # For other methods, use the default queryset
        return self.queryset
    
    @action(detail=False, methods=['delete'], url_path='delete')
    def delete(self, request, *args, **kwargs):
        ids_to_delete = request.data.get('ids', []) 
        SlurpitPlan.objects.filter(plan_id__in=ids_to_delete).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class SlurpitDeviceViewSet(
        BulkCreateModelMixin,
        BulkDestroyModelMixin,
        NetBoxModelViewSet
    ):
    queryset = SlurpitDevice.objects.all()
    serializer_class = SlurpitDeviceSerializer
    filterset_class = SlurpitDeviceFilterSet

    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request, *args, **kwargs):
        """
        A custom action to delete all SlurpitPlan objects.
        Be careful with this operation: it cannot be undone!
        """
        hostname = request.query_params.get('hostname', None)
        plan_id = request.query_params.get('plan_id', None)

        if hostname and plan_id:
            self.queryset = SlurpitDevice.objects.filter(hostname=hostname, plan_id=plan_id)
            # Perform the deletion and return a response
            self.queryset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)