from django.urls import include, path
from netbox.views.generic import ObjectChangeLogView
from . import views
from . import models


urlpatterns = (    
    ## setting ##
    path("settings/",           views.SettingsView.as_view(), name="settings"),
    
    ## onboard device ##
    path('devices/',            views.SlurpitImportedDeviceListView.as_view(), name='slurpitimporteddevice_list'),
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
    path('slurpitprefix/', views.SlurpitPrefixListView.as_view(), name='slurpitprefix_list'),
    path('slurpitinterface/', views.SlurpitInterfaceListView.as_view(), name='slurpitinterface_list'),
    path('slurpitvlan/', views.SlurpitVlanListView.as_view(), name='slurpitvlan_list'),

    path('slurpitinterface/<int:pk>/edit/', views.SlurpitInterfaceEditView.as_view(), name='slurpitinterface_edit'),
    path('slurpitipaddress/<int:pk>/edit/', views.SlurpitIPAddressEditView.as_view(), name='slurpitipaddress_edit'),
    path('slurpitprefix/<int:pk>/edit/', views.SlurpitPrefixEditView.as_view(), name='slurpitprefix_edit'),
    path('slurpitvlan/<int:pk>/edit/', views.SlurpitVLANEditView.as_view(), name='slurpitvlan_edit'),

    path('slurpitprefix/edit/', views.SlurpitPrefixBulkEditView.as_view(), name='slurpitprefix_bulk_edit'),
    path('slurpitipaddress/edit/', views.SlurpitIPAddressBulkEditView.as_view(), name='slurpitipaddress_bulk_edit'),
    path('slurpitinterface/edit/', views.SlurpitInterfaceBulkEditView.as_view(), name='slurpitinterface_bulk_edit'),
    path('slurpitvlan/edit/', views.SlurpitVLANBulkEditView.as_view(), name='slurpitvlan_bulk_edit'),
)
