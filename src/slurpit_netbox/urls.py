from django.urls import path

from . import views


urlpatterns = (
    path('devices/', views.ImportedDeviceListView.as_view(),
         name='importeddevice_list'),
    path('devices/onboard', views.ImportedDeviceOnboardView.as_view(),
         name='onboard'),
    path('devices/import', views.ImportDevices.as_view(), name='import')
)
