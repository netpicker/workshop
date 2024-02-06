import os

from django.apps import apps
from django.db.models.signals import post_migrate
from extras.plugins import PluginConfig, get_plugin_config

class SlurpitConfig(PluginConfig):
    name = "slurpit_netbox"
    verbose_name = "Slurp'it Plugin"
    description = "Sync Slurp'it into NetBox"
    version = '0.8.46'
    base_url = "slurpit"   
    default_settings = {
        'DeviceType': {'model': "Slurp'it", 'slug': 'slurpit'},
        'DeviceRole': {'name': "Slurp'it", 'slug': 'slurpit'},
        'Site': {'name': "Slurp'it", 'slug': 'slurpit'},
        'Location': {'name': 'Slurp\'it', 'slug': 'slurpit'},
        'Region': {'name': 'Slurp\'it', 'slug': 'slurpit'},
        'SiteGroup': {'name': 'Slurp\'it', 'slug': 'slurpit'}, 
        'Rack': {'name': 'Slurp\'it'},
        'ConfigTemplate': {'name': 'Slurp\'it'},
        'Manufacturer': {'name': 'OEM', 'slug': 'oem'},
        'unattended_import': False,
        'version': version
    }

    def ready(self):
        from .models import post_migration
        deps_app = apps.get_app_config("virtualization")
        post_migrate.connect(post_migration, sender=deps_app, weak=False)
        super().ready()


config = SlurpitConfig


def get_config(cfg):
    return get_plugin_config(get_config.__module__, cfg)

