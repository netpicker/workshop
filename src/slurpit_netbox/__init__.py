import os

from django.apps import apps
from django.db.models.signals import post_migrate
from extras.plugins import PluginConfig, get_plugin_config

class SlurpitConfig(PluginConfig):
    name = "slurpit_netbox"
    verbose_name = "Slurp'it Plugin"
    description = "Sync Slurp'it into NetBox"
    version = '0.8.4'
    base_url = "slurpit"    
    default_settings = {
        'DeviceType': {'model': "SlurpIT"},
        'DeviceRole': {'name': "SlurpIT"},
        'Site': {'name': "SlurpIT"},
        'Location': {'name': 'SlurpIT'},
        'Region': {'name': 'SlurpIT'},
        'SiteGroup': {'name': 'SlurpIT'}, 
        'Rack': {'name': 'SlurpIT'},
        'ConfigTemplate': {'name': 'SlurpIT'},
        'unattended_import': False,
        'version': version,
        'DEVICETYPE_LIBRARY': os.environ.get('DEVICETYPE_LIBRARY'),
    }

    def ready(self):
        from .models import post_migration
        deps_app = apps.get_app_config("virtualization")
        post_migrate.connect(post_migration, sender=deps_app, weak=False)
        super().ready()


config = SlurpitConfig


def get_config(cfg):
    return get_plugin_config(get_config.__module__, cfg)

