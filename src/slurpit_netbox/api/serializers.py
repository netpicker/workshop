from netbox.api.serializers import NetBoxModelSerializer
from slurpit_netbox.models import SlurpitPlan

class SlurpitPlanSerializer(NetBoxModelSerializer):

    class Meta:
        model = SlurpitPlan
        fields = ["id", "name", "plan_id", "display"]