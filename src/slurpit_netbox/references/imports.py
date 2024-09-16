from netbox.views import generic
from netbox.api.viewsets import NetBoxModelViewSet
from utilities.exceptions import AbortRequest, PermissionsViolation
from utilities.forms import restrict_form_fields
from dcim.choices import DeviceStatusChoices
from dcim.models import  Manufacturer, Platform, DeviceType, Site, Device, DeviceRole
from dcim.api.serializers import DeviceSerializer
from dcim.filtersets import DeviceFilterSet
from ipam.models import *
from extras.models import CustomField