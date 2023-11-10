from extras.plugins import PluginMenuButton, PluginMenuItem
from utilities.choices import ButtonColorChoices


imported_device_buttons = [
    PluginMenuButton(
        link='plugins:slurpit_netbox:import',
        title='Import',
        icon_class='mdi mdi-download',
        color=ButtonColorChoices.PURPLE,
    )
]

menu_items = (
    PluginMenuItem(
        link='plugins:slurpit_netbox:importeddevice_list',
        link_text='Imported Devices',
        buttons=imported_device_buttons,
    ),
)
