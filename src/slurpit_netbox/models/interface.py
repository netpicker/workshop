from netbox.models import PrimaryModel
from django.db import models
from dcim.models import CabledObjectModel, PathEndpoint, InventoryItem
from utilities.tracking import TrackingModelMixin
from utilities.ordering import naturalize_interface
from utilities.fields import NaturalOrderingField
from dcim.choices import InterfaceTypeChoices, InterfaceDuplexChoices, InterfaceModeChoices
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericRelation
from netbox.models import NetBoxModel
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from dcim.fields import MACAddressField
from django.core.validators import MaxValueValidator, MinValueValidator
from dcim.constants import INTERFACE_MTU_MIN, INTERFACE_MTU_MAX
from urllib.parse import urlencode

class ComponentModel(NetBoxModel):
    """
    An abstract model inherited by any model which has a parent Device.
    """
    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        null=True
    )
    name = models.CharField(
        verbose_name=_('name'),
        max_length=64,
        blank=True
    )
    _name = NaturalOrderingField(
        target_field='name',
        max_length=100,
        blank=True
    )
    label = models.CharField(
        verbose_name=_('label'),
        max_length=64,
        blank=True,
        help_text=_('Physical label')
    )
    description = models.CharField(
        verbose_name=_('description'),
        max_length=200,
        blank=True
    )

    class Meta:
        abstract = True
        ordering = ('_name')
        constraints = (
            models.UniqueConstraint(
                fields=('name'),
                name='%(app_label)s_%(class)s_unique_name'
            ),
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def __str__(self):
        if self.label:
            return f"{self.name} ({self.label})"
        return self.name

    def to_objectchange(self, action):
        objectchange = super().to_objectchange(action)
        return objectchange

    def clean(self):
        super().clean()


    
class ModularComponentModel(ComponentModel):
    module = models.ForeignKey(
        to='dcim.Module',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        blank=True,
        null=True
    )
    inventory_items = GenericRelation(
        to='dcim.InventoryItem',
        content_type_field='component_type',
        object_id_field='component_id'
    )

    class Meta(ComponentModel.Meta):
        abstract = True

class BaseInterface(models.Model):
    """
    Abstract base class for fields shared by dcim.Interface and virtualization.VMInterface.
    """
    enabled = models.BooleanField(
        verbose_name=_('enabled'),
        default=True
    )
    mac_address = MACAddressField(
        null=True,
        blank=True,
        verbose_name=_('MAC address')
    )
    mtu = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(INTERFACE_MTU_MIN),
            MaxValueValidator(INTERFACE_MTU_MAX)
        ],
        verbose_name=_('MTU')
    )
    mode = models.CharField(
        verbose_name=_('mode'),
        max_length=50,
        choices=InterfaceModeChoices,
        blank=True,
        help_text=_('IEEE 802.1Q tagging strategy')
    )
    parent = models.ForeignKey(
        to='self',
        on_delete=models.RESTRICT,
        related_name='child_interfaces',
        null=True,
        blank=True,
        verbose_name=_('parent interface')
    )
    bridge = models.ForeignKey(
        to='self',
        on_delete=models.SET_NULL,
        related_name='bridge_interfaces',
        null=True,
        blank=True,
        verbose_name=_('bridge interface')
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):

        # Remove untagged VLAN assignment for non-802.1Q interfaces
        if not self.mode:
            self.untagged_vlan = None

        return super().save(*args, **kwargs)

    @property
    def tunnel_termination(self):
        return self.tunnel_terminations.first()

    @property
    def count_ipaddresses(self):
        return self.ip_addresses.count()

    @property
    def count_fhrp_groups(self):
        return self.fhrp_group_assignments.count()
    
class SlurpitInterface(ModularComponentModel, BaseInterface, CabledObjectModel, PathEndpoint, TrackingModelMixin):
    # Override ComponentModel._name to specify naturalize_interface function
    _name = NaturalOrderingField(
        target_field='name',
        naturalize_function=naturalize_interface,
        max_length=100,
        blank=True
    )

    type = models.CharField(
        verbose_name=_('type'),
        max_length=50,
        choices=InterfaceTypeChoices
    )

    speed = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('speed (Kbps)')
    )
    
    duplex = models.CharField(
        verbose_name=_('duplex'),
        max_length=50,
        blank=True,
        null=True,
        choices=InterfaceDuplexChoices
    )

    enable_reconcile = models.BooleanField(
        default=False,
        verbose_name=_('enable reconcile'),
    )

    ignore_module = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore module'),
    )
    ignore_type = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore type'),
    )
    ignore_speed = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore speed'),
    )
    ignore_duplex = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore duplex'),
    )
    class Meta:
        verbose_name = _('Slurpit Device Interface')
        verbose_name_plural = _('Slurpit Device Interface')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"

    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('plugins:slurpit_netbox:reconcile_detail', args=[self.pk, 'interface'])

    def get_edit_url(self):
        query_params = {'tab': "interface"}
        base_url = reverse("plugins:slurpit_netbox:reconcile_list")
        # Encode your query parameters and append them to the base URL
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        base_url = reverse('plugins:slurpit_netbox:slurpitinterface_edit', args=[self.pk])
        query_params = {'return_url': url_with_querystring}
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        return url_with_querystring
