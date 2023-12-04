from extras.plugins import PluginTemplateExtension


class ImportedDeviceContent(PluginTemplateExtension):  # pylint: disable=abstract-method
    """Table to show onboarding details on Device objects."""

    model = "slurpit_netbox.importeddevice"

    def list_buttons(self):
        return "<div>CHECK</div>"
