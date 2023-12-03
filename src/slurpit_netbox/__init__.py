import os

from django.apps import apps
from django.db.models.signals import post_migrate
from extras.plugins import PluginConfig, get_plugin_config


class SlurpitConfig(PluginConfig):
    name = "slurpit_netbox"
    verbose_name = "Slurp'IT Plugin"
    description = "Sync Slurp'IT into NetBox"
    version = "0.0.1"
    base_url = "slurpit"
    required_settings = 'API_ENDPOINT', 'API_HEADERS'
    default_settings = {
        'DeviceType': {'model': "SlurpIT"},
        'DeviceRole': {'name': "SlurpIT"},
        'Site': {'name': "SlurpIT"},

        'netmiko_choices': 'netmiko_choices',
        'netmiko_handler': 'netmiko_handler',
        'unattended_import': False,
        'DEVICETYPE_LIBRARY': os.environ.get('DEVICETYPE_LIBRARY'),
    }

    def ready(self):
        from .models import post_migration
        dcim_app = apps.get_app_config("dcim")
        post_migrate.connect(post_migration, sender=dcim_app, weak=False)
        super().ready()


config = SlurpitConfig


def get_config(cfg):
    return get_plugin_config(get_config.__module__, cfg)
