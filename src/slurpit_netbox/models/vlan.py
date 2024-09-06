from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from netbox.models import OrganizationalModel, PrimaryModel
from ipam.constants import VLAN_VID_MIN, VLAN_VID_MAX
from ipam.choices import VLANStatusChoices
from ipam.querysets import VLANQuerySet, VLANGroupQuerySet
from dcim.models import Interface
from virtualization.models import VMInterface
from urllib.parse import urlencode

class SlurpitVLAN(PrimaryModel):
    """
    A VLAN is a distinct layer two forwarding domain identified by a 12-bit integer (1-4094). Each VLAN must be assigned
    to a Site, however VLAN IDs need not be unique within a Site. A VLAN may optionally be assigned to a VLANGroup,
    within which all VLAN IDs and names but be unique.

    Like Prefixes, each VLAN is assigned an operational status and optionally a user-defined Role. A VLAN can have zero
    or more Prefixes assigned to it.
    """
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='slurpit_vlans',
        blank=True,
        null=True,
        help_text=_("The specific site to which this VLAN is assigned (if any)")
    )
    group = models.ForeignKey(
        to='ipam.VLANGroup',
        on_delete=models.PROTECT,
        related_name='slurpit_vlans',
        blank=True,
        null=True,
        help_text=_("VLAN group (optional)")
    )
    group = models.CharField(
        verbose_name=_('group'),
        max_length=64,
        blank=True,
        null=True,
    )
    vid = models.PositiveSmallIntegerField(
        verbose_name=_('VLAN ID'),
        validators=(
            MinValueValidator(VLAN_VID_MIN),
            MaxValueValidator(VLAN_VID_MAX)
        ),
        help_text=_("Numeric VLAN ID (1-4094)")
    )
    name = models.CharField(
        verbose_name=_('name'),
        max_length=64,
        default = _(''),
        blank=True,
        null=True
    )
    tenant = models.ForeignKey(
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='slurpit_vlans',
        blank=True,
        null=True
    )
    status = models.CharField(
        verbose_name=_('status'),
        max_length=50,
        choices=VLANStatusChoices,
        default=VLANStatusChoices.STATUS_ACTIVE,
        help_text=_("Operational status of this VLAN")
    )
    role = models.ForeignKey(
        to='ipam.Role',
        on_delete=models.SET_NULL,
        related_name='slurpit_vlans',
        blank=True,
        null=True,
        help_text=_("The primary function of this VLAN")
    )

    enable_reconcile = models.BooleanField(
        default=False,
        verbose_name=_('enable reconcile'),
    )
    
    ignore_status = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore status'),
    )
    ignore_site = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore site'),
    )
    ignore_group = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore group'),
    )
    ignore_vid = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore vid'),
    )
    ignore_role = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore role'),
    )
    ignore_tenant = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore tenant'),
    )
    ignore_description = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore description'),
    )
    objects = VLANQuerySet.as_manager()

    clone_fields = [
        'site', 'tenant', 'status', 'role', 'description',
    ]

    class Meta:
        ordering = ('site', 'group', 'vid', 'pk')  # (site, group, vid) may be non-unique
        constraints = (
            models.UniqueConstraint(
                fields=('group', 'vid'),
                name='%(app_label)s_%(class)s_unique_group_vid'
            ),
            models.UniqueConstraint(
                fields=('group', 'name'),
                name='%(app_label)s_%(class)s_unique_group_name'
            ),
        )
        verbose_name = _('VLAN')
        verbose_name_plural = _('VLANs')

    def __str__(self):
        return f'{self.name} ({self.vid})'

    def get_absolute_url(self):
        return reverse('ipam:vlan', args=[self.pk])

    def clean(self):
        super().clean()

    def get_status_color(self):
        return VLANStatusChoices.colors.get(self.status)
    
    def get_edit_url(self):
        query_params = {'tab': "vlan"}
        base_url = reverse("plugins:slurpit_netbox:reconcile_list")
        # Encode your query parameters and append them to the base URL
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        base_url = reverse('plugins:slurpit_netbox:slurpitvlan_edit', args=[self.pk])
        query_params = {'return_url': url_with_querystring}
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        return url_with_querystring


