from extras.plugins import PluginMenuButton, PluginMenuItem, PluginMenu
from utilities.choices import ButtonColorChoices


imported_device_buttons = [
    PluginMenuButton(
        link='plugins:slurpit_netbox:import',
        title='Import',
        icon_class='mdi mdi-sync',
        color=ButtonColorChoices.ORANGE,
    )
]

menu = PluginMenu(
    label='Slurp`it',
    groups=(
        (
            'Slurp`it', (
                PluginMenuItem(
                    link='plugins:slurpit_netbox:settings',
                    link_text='Settings',
                    permissions=["slurpit_netbox.view_settings"]
                ),
                PluginMenuItem(
                    link='plugins:slurpit_netbox:importeddevice_list',
                    link_text='Onboard devices',
                    # buttons=imported_device_buttons,
                    permissions=["slurpit_netbox.view_onboard_devices"]
                ),
                PluginMenuItem(
                    link='plugins:slurpit_netbox:data_mapping_list',
                    link_text='Data mapping',
                    permissions=["slurpit_netbox.view_data_mapping"]
                ),
                PluginMenuItem(
                    link='plugins:slurpit_netbox:reconcile_list',
                    link_text='Reconcile',
                    permissions=["slurpit_netbox.view_reconcile"]
                ),
                PluginMenuItem(
                    link='plugins:slurpit_netbox:slurpitlog_list',
                    link_text='Logging',
                    permissions=["slurpit_netbox.view_logging"]
                ),
            )
        ),
    ),
    icon_class='mdi mdi-swap-horizontal'
)
