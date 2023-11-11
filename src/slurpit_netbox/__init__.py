from django.apps import apps
from django.db.models.signals import post_migrate
from extras.plugins import PluginConfig, get_plugin_config


class SlurpitConfig(PluginConfig):
    name = "slurpit_netbox"
    verbose_name = "SlurpIT Plugin"
    description = "Sync SlurpIT into NetBox"
    version = "0.0.1"
    base_url = "slurpit"
    required_settings = 'API_ENDPOINT', 'API_HEADERS'
    default_settings = {
        'DeviceType': {'model': 'SlurpIT'},
        'DeviceRole': {'name': 'SlurpIT'},
        'Site': {'name': 'SlurpIT'},

        'netmiko_choices': 'netmiko_choices',
        'netmiko_handler': 'netmiko_handler',
        'unattended_import': False,
        'devicetype_library': None,
    }

    def ready(self):
        from .models import ensure_default_instances
        dcim_app = apps.get_app_config("dcim")
        post_migrate.connect(ensure_default_instances, sender=dcim_app, weak=False)
        super().ready()


config = SlurpitConfig


def get_config(cfg):
    return get_plugin_config(get_config.__module__, cfg)
