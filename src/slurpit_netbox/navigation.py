from netbox.plugins import PluginMenuButton, PluginMenuItem, PluginMenu


imported_device_buttons = [
    PluginMenuButton(
        link='plugins:slurpit_netbox:import',
        title='Import',
        icon_class='mdi mdi-sync',
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
                    permissions=["slurpit_netbox.view_slurpitsetting"]
                ),
                PluginMenuItem(
                    link='plugins:slurpit_netbox:slurpitimporteddevice_list',
                    link_text='Onboard devices',
                    # buttons=imported_device_buttons,
                    permissions=["slurpit_netbox.view_slurpitstageddevice", "slurpit_netbox.view_slurpitimporteddevice"]
                ),
                PluginMenuItem(
                    link='plugins:slurpit_netbox:data_mapping_list',
                    link_text='Data mapping',
                    permissions=[
                        "slurpit_netbox.view_slurpitmapping",
                        "slurpit_netbox.view_slurpitprefix",
                        "slurpit_netbox.view_slurpitinitipaddress",
                        "slurpit_netbox.view_slurpitinterface",
                        "slurpit_netbox.view_slurpitvlan"
                    ]
                ),
                PluginMenuItem(
                    link='plugins:slurpit_netbox:reconcile_list',
                    link_text='Reconcile',
                    permissions=[
                        "slurpit_netbox.view_slurpitprefix",
                        "slurpit_netbox.view_slurpitinitipaddress",
                        "slurpit_netbox.view_slurpitinterface",
                        "slurpit_netbox.view_slurpitvlan"
                    ]
                ),
                PluginMenuItem(
                    link='plugins:slurpit_netbox:slurpitlog_list',
                    link_text='Logging',
                    permissions=["slurpit_netbox.view_slurpitlog"]
                ),
            )
        ),
    ),
    icon_class='mdi mdi-swap-horizontal',
)
