from extras.plugins import PluginTemplateExtension


class SlurpitImportedDeviceContent(PluginTemplateExtension):  # pylint: disable=abstract-method
    """Table to show onboarding details on Device objects."""

    model = "slurpit_netbox.slurpitimporteddevice"

    def list_buttons(self):
        return "<div>CHECK</div>"
