from django.core.management.base import BaseCommand

from slurpit_netbox.importer import import_devices


class Command(BaseCommand):
    help = "Generate JSON schema for validating NetBox device type definitions"

    def handle(self, *args, **kwargs):
        import_devices()