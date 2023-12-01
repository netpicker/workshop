from extras.plugins import PluginMenuButton, PluginMenuItem
from utilities.choices import ButtonColorChoices


imported_device_buttons = [
    PluginMenuButton(
        link='plugins:slurpit_netbox:import',
        title='Import',
        icon_class='mdi mdi-download',
        color=ButtonColorChoices.ORANGE,
    )
]

menu_items = (
    PluginMenuItem(
        link='plugins:slurpit_netbox:importeddevice_list',
        link_text='Settings',
    ),
    PluginMenuItem(
        link='plugins:slurpit_netbox:importeddevice_list',
        link_text='Onboard devices',
        buttons=imported_device_buttons,
    ),
    PluginMenuItem(
        link='plugins:slurpit_netbox:importeddevice_list',
        link_text='Data mapping',
    ),
    PluginMenuItem(
        link='plugins:slurpit_netbox:importeddevice_list',
        link_text='Reconcile',
    ),
    PluginMenuItem(
        link='plugins:slurpit_netbox:importeddevice_list',
        link_text='Logging',
    ),
)
