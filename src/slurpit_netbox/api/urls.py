from netbox.api.routers import NetBoxRouter
from . import views

router = NetBoxRouter()
router.APIRootView = views.SlurpitRootView
router.register("planning", views.SlurpitPlanningViewSet)
router.register("planning-data", views.SlurpitSnapshotViewSet)
router.register("device", views.DeviceViewSet)
router.register('test', views.SlurpitTestAPIView)
app_name = 'slurpit-api'
urlpatterns = router.urls
