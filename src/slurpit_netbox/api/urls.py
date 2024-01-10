from netbox.api.routers import NetBoxRouter
from slurpit_netbox.api.views import SlurpitPlanViewSet

router = NetBoxRouter()
router.register("plan", SlurpitPlanViewSet)
urlpatterns = router.urls
