import netaddr
from netbox.models import PrimaryModel
from django.db import models
from ipam.fields import IPAddressField
from ipam.choices import IPAddressStatusChoices, IPAddressRoleChoices
from ipam.constants import IPADDRESS_ASSIGNMENT_MODELS, IPADDRESS_ROLES_NONUNIQUE
from django.contrib.contenttypes.fields import GenericForeignKey
from ipam.validators import DNSValidator
from ipam.managers import IPAddressManager
from django.db.models.functions import Cast
from ipam.lookups import Host
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from netbox.config import get_config
from urllib.parse import urlencode

class SlurpitInitIPAddress(PrimaryModel):
    """
    An IPAddress represents an individual IPv4 or IPv6 address and its mask. The mask length should match what is
    configured in the real world. (Typically, only loopback interfaces are configured with /32 or /128 masks.) Like
    Prefixes, IPAddresses can optionally be assigned to a VRF. An IPAddress can optionally be assigned to an Interface.
    Interfaces can have zero or more IPAddresses assigned to them.

    An IPAddress can also optionally point to a NAT inside IP, designating itself as a NAT outside IP. This is useful,
    for example, when mapping public addresses to private addresses. When an Interface has been assigned an IPAddress
    which has a NAT outside IP, that Interface's Device can use either the inside or outside IP as its primary IP.
    """
    address = IPAddressField(
        verbose_name=_('address'),
        help_text=_('IPv4 or IPv6 address (with mask)'),
        blank=True,
        null=True
    )
    status = models.CharField(
        verbose_name=_('status'),
        max_length=50,
        choices=IPAddressStatusChoices,
        default=IPAddressStatusChoices.STATUS_ACTIVE,
        help_text=_('The operational status of this IP')
    )
    role = models.CharField(
        verbose_name=_('role'),
        max_length=50,
        choices=IPAddressRoleChoices,
        blank=True,
        help_text=_('The functional role of this IP')
    )

    vrf = models.ForeignKey(
        to='ipam.VRF',
        on_delete=models.PROTECT,
        related_name='slurpit_ip_addresses',
        blank=True,
        null=True,
        verbose_name=_('VRF')
    )
    tenant = models.ForeignKey(
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='slurpit_ip_addresses',
        blank=True,
        null=True
    )

    enable_reconcile = models.BooleanField(
        default=False,
        verbose_name=_('enable reconcile'),
    )

    dns_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        validators=[DNSValidator],
        verbose_name=_('DNS name'),
        help_text=_('Hostname or FQDN (not case-sensitive)')
    )

    ignore_status = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore status'),
    )
    ignore_role = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore role'),
    )
    ignore_vrf = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore vrf'),
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

    class Meta:
        verbose_name = _('Slurpit IP address')
        verbose_name_plural = _('Slurpit  IP addresses')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.address}"
    
    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_status_color(self):
        return IPAddressStatusChoices.colors.get(self.status)
    
    def get_absolute_url(self):
        return reverse('plugins:slurpit_netbox:reconcile_detail', args=[self.pk, 'ipam'])
    
    def get_edit_url(self):
        query_params = {'tab': "ipam"}
        base_url = reverse("plugins:slurpit_netbox:reconcile_list")
        # Encode your query parameters and append them to the base URL
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        base_url = reverse('plugins:slurpit_netbox:slurpitipaddress_edit', args=[self.pk])
        query_params = {'return_url': url_with_querystring}
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        return url_with_querystring