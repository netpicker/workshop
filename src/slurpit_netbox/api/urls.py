from netbox.api.routers import NetBoxRouter
from . import views

router = NetBoxRouter()
router.APIRootView = views.SlurpitRootView
router.register("plan", views.SlurpitPlanViewSet)
router.register("slurpitdevice", views.SlurpitDeviceViewSet)

app_name = 'slurpit-api'
urlpatterns = router.urls
