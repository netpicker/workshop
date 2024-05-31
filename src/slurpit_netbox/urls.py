from django.urls import include, path
from utilities.urls import get_model_urls
from netbox.views.generic import ObjectChangeLogView
from . import views
from . import models


urlpatterns = (    
    ## setting ##
    path("settings/",           views.SettingsView.as_view(), name="settings"),
    
    ## onboard device ##
    path('devices/',            views.SlurpitImportedDeviceListView.as_view(), name='importeddevice_list'),
    path('devices/onboard',     views.SlurpitImportedDeviceOnboardView.as_view(), name='onboard'),
    path('devices/import',      views.ImportDevices.as_view(), name='import'),

    ## data mapping ##
    path('data_mapping/',       views.DataMappingView.as_view(), name='data_mapping_list'),

    ## reconcile ##
    path('reconcile/',          views.ReconcileView.as_view(), name='reconcile_list'),
    path('reconcile/<int:pk>/<str:reconcile_type>', views.ReconcileDetailView.as_view(), name='reconcile_detail'),
    ## logging ##
    path('slurpitlog/',         views.LoggingListView.as_view(), name='slurpitlog_list'),
    

    path('slurpitinitaddress/', views.SlurpitInitIPAddressListView.as_view(), name='slurpitinitipaddress_list'),
    path('slurpitprefix/', views.SlurpitInitIPAddressListView.as_view(), name='slurpitprefix_list'),
    path('slurpitinterface/', views.SlurpitInitIPAddressListView.as_view(), name='slurpitinterface_list'),

)
