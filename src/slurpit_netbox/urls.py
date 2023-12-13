from django.urls import include, path
from utilities.urls import get_model_urls
from netbox.views.generic import ObjectChangeLogView
from . import views
from . import models


urlpatterns = (
    path("planning/<int:pk>/",  views.PlanningListView.as_view(), name="planning_list"),
    
    ## setting ##
    path("source/",             views.SourceListView.as_view(), name="source_list"),
    path("source/add/",         views.SourceEditView.as_view(), name="source_add"),
    path("source/delete/",      views.SourceBulkDeleteView.as_view(), name="source_bulk_delete"),
    path("source/<int:pk>/delete/", views.SourceDeleteView.as_view(), name="source_delete"),
    path("source/<int:pk>/",     include(get_model_urls("slurpit_netbox", "source"))),
    
    ## onboard device ##
    path('devices/',            views.ImportedDeviceListView.as_view(), name='importeddevice_list'),
    path('devices/onboard',     views.ImportedDeviceOnboardView.as_view(), name='onboard'),
    path('devices/import',      views.ImportDevices.as_view(), name='import'),

    ## data mapping ##
    path('data_mapping/',       views.DataMappingView.as_view(), name='data_mapping_list'),

    ## reconcile ##
    path('reconcile/',          views.ReconcileView.as_view(), name='reconcile_list'),

    ## logging ##
    path('slurpitlog/',            views.LoggingListView.as_view(), name='slurpitlog_list'),
)
