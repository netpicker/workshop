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
        'unattended_import': False
    }


config = SlurpitConfig


def get_config(cfg):
    return get_plugin_config(get_config.__module__, cfg)
