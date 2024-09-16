from ipam.models import IPAddress, IPRange
from ipam.fields import IPNetworkField
from django.utils.translation import gettext_lazy as _
from django.db.models import F
from django.urls import reverse
from django.db import models
from netbox.models import PrimaryModel
import netaddr
from ipam.choices import PrefixStatusChoices
from ipam.querysets import PrefixQuerySet
from netbox.config import get_config
from django.core.exceptions import ValidationError
from urllib.parse import urlencode
class GetAvailablePrefixesMixin:

    def get_available_prefixes(self):
        """
        Return all available prefixes within this Aggregate or Prefix as an IPSet.
        """
        params = {
            'prefix__net_contained': str(self.prefix)
        }
        if hasattr(self, 'vrf'):
            params['vrf'] = self.vrf

        child_prefixes = SlurpitPrefix.objects.filter(**params).values_list('prefix', flat=True)
        return netaddr.IPSet(self.prefix) - netaddr.IPSet(child_prefixes)

    def get_first_available_prefix(self):
        """
        Return the first available child prefix within the prefix (or None).
        """
        available_prefixes = self.get_available_prefixes()
        if not available_prefixes:
            return None
        return available_prefixes.iter_cidrs()[0]
    

class SlurpitPrefix(GetAvailablePrefixesMixin, PrimaryModel):
    prefix = IPNetworkField(
        verbose_name=_('prefix'),
        help_text=_('IPv4 or IPv6 network with mask'),
        blank=True,
        null=True
    )
    
    enable_reconcile = models.BooleanField(
        default=False,
        verbose_name=_('enable reconcile'),
    )

    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='slurpit_prefixes',
        blank=True,
        null=True
    )
    vrf = models.ForeignKey(
        to='ipam.VRF',
        on_delete=models.PROTECT,
        related_name='slurpit_prefixes',
        blank=True,
        null=True,
        verbose_name=_('VRF')
    )
    tenant = models.ForeignKey(
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='slurpit_prefixes',
        blank=True,
        null=True
    )
    vlan = models.ForeignKey(
        to='ipam.VLAN',
        on_delete=models.PROTECT,
        related_name='slurpit_prefixes',
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=50,
        choices=PrefixStatusChoices,
        default=PrefixStatusChoices.STATUS_ACTIVE,
        verbose_name=_('status'),
        help_text=_('Operational status of this prefix')
    )
    role = models.ForeignKey(
        to='ipam.Role',
        on_delete=models.SET_NULL,
        related_name='slurpit_prefixes',
        blank=True,
        null=True,
        help_text=_('The primary function of this prefix')
    )
    is_pool = models.BooleanField(
        verbose_name=_('is a pool'),
        default=False,
        help_text=_('All IP addresses within this prefix are considered usable')
    )
    mark_utilized = models.BooleanField(
        verbose_name=_('mark utilized'),
        default=False,
        help_text=_("Treat as fully utilized")
    )

    ignore_status = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore status'),
    )
    ignore_vrf = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore vrf'),
    )
    ignore_role = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore role'),
    )
    ignore_site = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore site'),
    )
    ignore_vlan = models.BooleanField(
        default=False,
        null=True,
        verbose_name=_('ignore vlan'),
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
    

    # Cached depth & child counts
    _depth = models.PositiveSmallIntegerField(
        default=0,
        editable=False
    )
    _children = models.PositiveBigIntegerField(
        default=0,
        editable=False
    )

    objects = PrefixQuerySet.as_manager()

    clone_fields = (
        'site', 'vrf', 'tenant', 'vlan', 'status', 'role', 'is_pool', 'mark_utilized', 'description',
    )

    class Meta:
        ordering = (F('vrf').asc(nulls_first=True), 'prefix', 'pk')  # (vrf, prefix) may be non-unique
        verbose_name = _('Slurpit Prefix')
        verbose_name_plural = _('Slurpit Prefixes')
    
    def get_absolute_url(self):
        return reverse('plugins:slurpit_netbox:reconcile_detail', args=[self.pk, 'prefix'])
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Cache the original prefix and VRF so we can check if they have changed on post_save
        self._prefix = self.__dict__.get('prefix')
        self._vrf_id = self.__dict__.get('vrf_id')

    def __str__(self):
        return str(self.prefix)

    def clean(self):
        super().clean()

        if self.prefix:

            # /0 masks are not acceptable
            if self.prefix.prefixlen == 0:
                raise ValidationError({
                    'prefix': _("Cannot create prefix with /0 mask.")
                })

            # Enforce unique IP space (if applicable)
            if (self.vrf is None and get_config().ENFORCE_GLOBAL_UNIQUE) or (self.vrf and self.vrf.enforce_unique):
                duplicate_prefixes = self.get_duplicates()
                if duplicate_prefixes:
                    table = _("VRF {vrf}").format(vrf=self.vrf) if self.vrf else _("global table")
                    raise ValidationError({
                        'prefix': _("Duplicate prefix found in {table}: {prefix}").format(
                            table=table,
                            prefix=duplicate_prefixes.first(),
                        )
                    })

    def save(self, *args, **kwargs):

        if isinstance(self.prefix, netaddr.IPNetwork):

            # Clear host bits from prefix
            self.prefix = self.prefix.cidr

        super().save(*args, **kwargs)

    @property
    def family(self):
        return self.prefix.version if self.prefix else None

    @property
    def mask_length(self):
        return self.prefix.prefixlen if self.prefix else None

    @property
    def depth(self):
        return self._depth

    @property
    def children(self):
        return self._children

    def _set_prefix_length(self, value):
        """
        Expose the IPNetwork object's prefixlen attribute on the parent model so that it can be manipulated directly,
        e.g. for bulk editing.
        """
        if self.prefix is not None:
            self.prefix.prefixlen = value
    prefix_length = property(fset=_set_prefix_length)

    def get_status_color(self):
        return PrefixStatusChoices.colors.get(self.status)

    def get_parents(self, include_self=False):
        """
        Return all containing Prefixes in the hierarchy.
        """
        lookup = 'net_contains_or_equals' if include_self else 'net_contains'
        return SlurpitPrefix.objects.filter(**{
            'vrf': self.vrf,
            f'prefix__{lookup}': self.prefix
        })

    def get_children(self, include_self=False):
        """
        Return all covered Prefixes in the hierarchy.
        """
        lookup = 'net_contained_or_equal' if include_self else 'net_contained'
        return SlurpitPrefix.objects.filter(**{
            'vrf': self.vrf,
            f'prefix__{lookup}': self.prefix
        })

    def get_duplicates(self):
        return SlurpitPrefix.objects.filter(vrf=self.vrf, prefix=str(self.prefix)).exclude(pk=self.pk)

    def get_child_prefixes(self):
        """
        Return all Prefixes within this Prefix and VRF. If this Prefix is a container in the global table, return child
        Prefixes belonging to any VRF.
        """
        if self.vrf is None and self.status == PrefixStatusChoices.STATUS_CONTAINER:
            return SlurpitPrefix.objects.filter(prefix__net_contained=str(self.prefix))
        else:
            return SlurpitPrefix.objects.filter(prefix__net_contained=str(self.prefix), vrf=self.vrf)

    def get_child_ranges(self):
        """
        Return all IPRanges within this Prefix and VRF.
        """
        return IPRange.objects.filter(
            vrf=self.vrf,
            start_address__net_host_contained=str(self.prefix),
            end_address__net_host_contained=str(self.prefix)
        )

    def get_child_ips(self):
        """
        Return all IPAddresses within this Prefix and VRF. If this Prefix is a container in the global table, return
        child IPAddresses belonging to any VRF.
        """
        if self.vrf is None and self.status == PrefixStatusChoices.STATUS_CONTAINER:
            return IPAddress.objects.filter(address__net_host_contained=str(self.prefix))
        else:
            return IPAddress.objects.filter(address__net_host_contained=str(self.prefix), vrf=self.vrf)

    def get_available_ips(self):
        """
        Return all available IPs within this prefix as an IPSet.
        """
        if self.mark_utilized:
            return netaddr.IPSet()

        prefix = netaddr.IPSet(self.prefix)
        child_ips = netaddr.IPSet([ip.address.ip for ip in self.get_child_ips()])
        child_ranges = []
        for iprange in self.get_child_ranges():
            child_ranges.append(iprange.range)
        available_ips = prefix - child_ips - netaddr.IPSet(child_ranges)

        # IPv6 /127's, pool, or IPv4 /31-/32 sets are fully usable
        if (self.family == 6 and self.prefix.prefixlen >= 127) or self.is_pool or (self.family == 4 and self.prefix.prefixlen >= 31):
            return available_ips

        if self.family == 4:
            # For "normal" IPv4 prefixes, omit first and last addresses
            available_ips -= netaddr.IPSet([
                netaddr.IPAddress(self.prefix.first),
                netaddr.IPAddress(self.prefix.last),
            ])
        else:
            # For IPv6 prefixes, omit the Subnet-Router anycast address
            # per RFC 4291
            available_ips -= netaddr.IPSet([netaddr.IPAddress(self.prefix.first)])
        return available_ips

    def get_first_available_ip(self):
        """
        Return the first available IP within the prefix (or None).
        """
        available_ips = self.get_available_ips()
        if not available_ips:
            return None
        return '{}/{}'.format(next(available_ips.__iter__()), self.prefix.prefixlen)

    def get_utilization(self):
        """
        Determine the utilization of the prefix and return it as a percentage. For Prefixes with a status of
        "container", calculate utilization based on child prefixes. For all others, count child IP addresses.
        """
        if self.mark_utilized:
            return 100

        if self.status == PrefixStatusChoices.STATUS_CONTAINER:
            queryset = SlurpitPrefix.objects.filter(
                prefix__net_contained=str(self.prefix),
                vrf=self.vrf
            )
            child_prefixes = netaddr.IPSet([p.prefix for p in queryset])
            utilization = float(child_prefixes.size) / self.prefix.size * 100
        else:
            # Compile an IPSet to avoid counting duplicate IPs
            child_ips = netaddr.IPSet(
                [_.range for _ in self.get_child_ranges()] + [_.address.ip for _ in self.get_child_ips()]
            )

            prefix_size = self.prefix.size
            if self.prefix.version == 4 and self.prefix.prefixlen < 31 and not self.is_pool:
                prefix_size -= 2
            utilization = float(child_ips.size) / prefix_size * 100

        return min(utilization, 100)

    def get_edit_url(self):
        query_params = {'tab': "prefix"}
        base_url = reverse("plugins:slurpit_netbox:reconcile_list")
        # Encode your query parameters and append them to the base URL
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        base_url = reverse('plugins:slurpit_netbox:slurpitprefix_edit', args=[self.pk])
        query_params = {'return_url': url_with_querystring}
        url_with_querystring = f"{base_url}?{urlencode(query_params)}"

        return url_with_querystring
