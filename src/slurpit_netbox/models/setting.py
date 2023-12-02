import ast
import json
import logging
import traceback
from copy import deepcopy

import httpx
import requests
from core.choices import DataSourceStatusChoices
from core.exceptions import SyncError
from core.models import Job
from core.signals import pre_sync
from dcim.models import VirtualChassis
from dcim.signals import assign_virtualchassis_master
from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models import signals
from django.urls import reverse
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from extras.models import Branch
from netbox.models import ChangeLoggedModel
from netbox.models import NetBoxModel
from netbox.models import PrimaryModel
from netbox.models.features import JobsMixin
from netbox.models.features import TagsMixin
from netbox.registry import registry
from netbox.staging import checkout
from utilities.querysets import RestrictedQuerySet
from utilities.utils import serialize_object
from utilities.utils import shallow_compare_dict

from slurpit_netbox.slurpitch import SlurpitSession

# from .choices import IPFabricSnapshotStatusModelChoices
# from .choices import IPFabricSyncTypeChoices
# from .choices import IPFabricTransformMapSourceModelChoices
# from .utilities.ipfutils import IPFabric
# from .utilities.ipfutils import IPFabricSyncRunner
# from .utilities.ipfutils import render_jinja2
# from .utilities.logging import SyncLogging


logger = logging.getLogger("ipfabric_netbox.models")


def apply_tags(object, tags):
    def _apply(object):
        for tag in tags:
            if hasattr(object, "tags"):
                object.tags.add(tag)
        object.save()
    _apply(object)


# IPFabricSupportedSyncModels = Q(
#     Q(app_label="dcim", model="site")
#     | Q(app_label="dcim", model="manufacturer")
#     | Q(app_label="dcim", model="platform")
#     | Q(app_label="dcim", model="devicerole")
#     | Q(app_label="dcim", model="devicetype")
#     | Q(app_label="dcim", model="device")
#     | Q(app_label="dcim", model="virtualchassis")
#     | Q(app_label="dcim", model="interface")
#     | Q(app_label="ipam", model="vlan")
#     | Q(app_label="ipam", model="vrf")
#     | Q(app_label="ipam", model="prefix")
#     | Q(app_label="ipam", model="ipaddress")
#     | Q(app_label="contenttypes", model="contenttype")
#     # TODO: Inventory Item broken util https://github.com/netbox-community/netbox/issues/13422 is resolved
#     # | Q(app_label="dcim", model="inventoryitem")
# )
#
#
# IPFabricRelationshipFieldSourceModels = Q(
#     Q(app_label="dcim")
#     | Q(app_label="ipam")
#     | Q(app_label="contenttypes", model="contenttype")
# )
#
#
# class IPFabricTransformMap(NetBoxModel):
#     name = models.CharField(max_length=100, unique=True)
#     source_model = models.CharField(
#         max_length=50, choices=IPFabricTransformMapSourceModelChoices
#     )
#     target_model = models.ForeignKey(
#         to=ContentType,
#         related_name="+",
#         verbose_name="Target Model",
#         limit_choices_to=IPFabricSupportedSyncModels,
#         help_text=_("The object(s) to which transform map target applies."),
#         on_delete=models.PROTECT,
#         blank=False,
#         null=False,
#     )
#     status = models.CharField(
#         max_length=50,
#     )
#
#     class Meta:
#         verbose_name = "IP Fabric Transform Map"
#         verbose_name_plural = "IP Fabric Transform Maps"
#
#     def __str__(self):
#         if self.source_model and self.target_model:
#             return f"{self.source_model} - {self.target_model}"
#         else:
#             return "Transform Map"
#
#     def get_absolute_url(self):
#         return reverse("plugins:ipfabric_netbox:ipfabrictransformmap", args=[self.pk])
#
#     @property
#     def docs_url(self):
#         # TODO: Add docs url
#         return ""
#
#     def get_models(self):
#         _context = dict()
#
#         for app, model_names in registry["model_features"]["custom_fields"].items():
#             _context.setdefault(app, {})
#             for model_name in model_names:
#                 model = apps.get_registered_model(app, model_name)
#                 _context[app][model.__name__] = model
#         _context["contenttypes"] = {}
#         _context["contenttypes"]["ContentType"] = ContentType
#         return _context
#
#     def build_relationships(self, uuid, source_data):
#         relationship_maps = self.relationship_maps.all()
#         rel_dict = {}
#         rel_dict_coalesce = {}
#
#         for field in relationship_maps:
#             if field.template:
#                 context = {
#                     "object": source_data,
#                 }
#                 context.update(self.get_models())
#                 text = render_jinja2(field.template, context).strip()
#                 if text:
#                     try:
#                         pk = int(text)
#                     except ValueError:
#                         pk = text
#
#                     if isinstance(pk, int):
#                         related_object = field.source_model.model_class().objects.get(
#                             pk=pk
#                         )
#                     else:
#                         related_object = ast.literal_eval(pk)
#
#                     if not field.coalesce:
#                         rel_dict[field.target_field] = related_object
#                     else:
#                         rel_dict_coalesce[field.target_field] = related_object
#             elif uuid and self.relationship_store.get(uuid):
#                 object = self.relationship_store[uuid].get(
#                     field.source_model.model_class()
#                 )
#                 if object:
#                     if not field.coalesce:
#                         rel_dict[field.target_field] = object
#                     else:
#                         rel_dict_coalesce[field.target_field] = object
#
#         return rel_dict, rel_dict_coalesce
#
#     def update_or_create_instance(
#         self, data, tags=[], uuid=None, relationship_store={}, logger=None
#     ):
#         self.relationship_store = relationship_store
#         new_data = deepcopy(data)
#         relationship, coalesce_relationship = self.build_relationships(
#             uuid=uuid, source_data=data
#         )
#
#         if relationship:
#             new_data["relationship"] = relationship
#         if coalesce_relationship:
#             new_data["relationship_coalesce"] = coalesce_relationship
#         context = self.render(new_data)
#         try:
#             instance, _ = self.target_model.model_class().objects.update_or_create(
#                 **context
#             )
#             if instance:
#                 apply_tags(instance, tags)
#         except Exception as e:
#             error_message = f"""Failed to create instance:<br/>
#             message: `{e}`<br/>
#             raw data: `{data}`<br/>
#             context: `{context}`<br/>
#             """
#             logger.log_failure(error_message, obj=self)
#             logger.log_failure(
#                 "Ensure that all transform map fields are present.", obj=self
#             )
#             raise SyncError("Unable to update_or_create_instance.")
#
#         return instance
#
#     def get_coalesce_fields(self, source_data):
#         data = self.render(source_data)
#         del data["defaults"]
#         return data
#
#     def render(self, source_data):
#         data = {"defaults": {}}
#         for field in self.field_maps.all():
#             if field.template:
#                 context = {
#                     "object": source_data,
#                     field.source_field: source_data[field.source_field],
#                 }
#                 context.update(self.get_models())
#                 text = render_jinja2(field.template, context).strip()
#             else:
#                 text = source_data[field.source_field]
#
#             if text is not None:
#                 if isinstance(text, str):
#                     if text.lower() in ["true"]:
#                         text = True
#                     elif text.lower() in ["false"]:
#                         text = False
#                     elif text.lower() in ["none"]:
#                         text = None
#
#                     if text:
#                         target_field = getattr(
#                             self.target_model.model_class(), field.target_field
#                         )
#                         target_field_type = target_field.field.get_internal_type()
#                         if "integer" in target_field_type.lower():
#                             text = int(text)
#
#             if not field.coalesce:
#                 data["defaults"][field.target_field] = text
#             else:
#                 data[field.target_field] = text
#
#         if relationship := source_data.get("relationship"):
#             data["defaults"].update(relationship)
#
#         if relationship_coalesce := source_data.get("relationship_coalesce"):
#             data.update(relationship_coalesce)
#
#         if self.status:
#             data["defaults"]["status"] = self.status
#
#         return data
#
#
# class IPFabricRelationshipField(models.Model):
#     transform_map = models.ForeignKey(
#         to=IPFabricTransformMap,
#         on_delete=models.CASCADE,
#         related_name="relationship_maps",
#         editable=True,
#     )
#     source_model = models.ForeignKey(
#         ContentType,
#         related_name="ipfabric_transform_fields",
#         limit_choices_to=IPFabricRelationshipFieldSourceModels,
#         verbose_name="Source Model",
#         on_delete=models.PROTECT,
#         blank=False,
#         null=False,
#     )
#     target_field = models.CharField(max_length=100)
#     coalesce = models.BooleanField(default=False)
#     template = models.TextField(
#         help_text=_(
#             "Jinja2 template code, return an integer to create a relationship between the source and target model. True, False and None are also supported."
#         ),
#         blank=True,
#         null=True,
#     )
#
#     objects = RestrictedQuerySet.as_manager()
#
#     class Meta:
#         ordering = ("transform_map",)
#         verbose_name = "IP Fabric Relationship Field"
#         verbose_name_plural = "IP Fabric Relationship Fields"
#
#     @property
#     def docs_url(self):
#         # TODO: Add docs url
#         return ""
#
#
# class IPFabricTransformField(models.Model):
#     transform_map = models.ForeignKey(
#         to=IPFabricTransformMap,
#         on_delete=models.CASCADE,
#         related_name="field_maps",
#         editable=True,
#     )
#     source_field = models.CharField(max_length=100)
#     target_field = models.CharField(max_length=100)
#     coalesce = models.BooleanField(default=False)
#
#     objects = RestrictedQuerySet.as_manager()
#
#     template = models.TextField(
#         help_text=_("Jinja2 template code to be rendered into the target field."),
#         blank=True,
#         null=True,
#     )
#
#     class Meta:
#         ordering = ("transform_map",)
#         verbose_name = "IP Fabric Transform Field"
#         verbose_name_plural = "IP Fabric Transform Fields"
#
#     @property
#     def docs_url(self):
#         # TODO: Add docs url
#         return ""
#
#
# class IPFabricClient:
#     def get_client(self, parameters, transform_map=None):
#         try:
#             if transform_map:
#                 ipf = IPFabric(parameters=parameters, transform_map=transform_map)
#             else:
#                 ipf = IPFabric(parameters=parameters)
#             return ipf.ipf
#         except httpx.ConnectError as e:
#             if "CERTIFICATE_VERIFY_FAILED" in str(e):
#                 error_message = (
#                     "SSL certificate verification failed, self-signed cert? "
#                     "<a href='https://docs.ipfabric.io/main/integrations/netbox-plugin/user_guide/10_FAQ/' target='_blank'>Check out our FAQ documentation.</a>"
#                 )
#             else:
#                 error_message = str(e)
#             self.handle_sync_failure("ConnectError", e, error_message)
#         except httpx.HTTPStatusError as e:
#             if e.response.status_code == 401:
#                 error_message = "Authentication failed, check API key."
#             else:
#                 error_message = str(e)
#             self.handle_sync_failure("HTTPStatusError", e, error_message)
#         return None
#
#     def handle_sync_failure(self, failure_type, exception, message=None):
#         self.status = DataSourceStatusChoices.FAILED
#
#         if message:
#             self.logger.log_failure(
#                 f"{message} ({failure_type}): `{exception}`", obj=self
#             )
#         else:
#             self.logger.log_failure(f"Syncing Snapshot Failed: `{exception}`", obj=self)


class Source(PrimaryModel):
    name = models.CharField(max_length=100, unique=True)
    url = models.CharField(max_length=200, verbose_name=_("URL"))
    status = models.CharField(
        max_length=50,
        choices=DataSourceStatusChoices,
        default=DataSourceStatusChoices.NEW,
        editable=False,
    )
    parameters = models.JSONField(blank=True, null=True)
    last_synced = models.DateTimeField(blank=True, null=True, editable=False)

    class Meta:
        ordering = ("name",)
        verbose_name = "Data source"
        verbose_name_plural = "Data sources"

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse("plugins:slurpit_netbox:source", args=[self.pk])

    def get_session(self):
        ssl_verify = self.parameters.get('verify', True)
        token = self.parameters.get('auth')
        return SlurpitSession(self.url, token, ssl_verify)

    @property
    def ready_for_sync(self):
        return self.status not in (
            DataSourceStatusChoices.QUEUED,
            DataSourceStatusChoices.SYNCING,
        )

    @property
    def docs_url(self):
        # TODO: Add docs url
        return ""

    def clean(self):
        super().clean()

        self.url = self.url.rstrip("/")

    def enqueue_sync_job(self, request):
        # Set the status to "syncing"
        self.status = DataSourceStatusChoices.QUEUED
        Source.objects.filter(pk=self.pk).update(status=self.status)

        # Enqueue a sync job
        return Job.enqueue(
            import_string("slurpit_netbox.jobs.sync_source"),
            name=f"{self.name} Sync",
            instance=self,
            user=request.user,
        )

    # def sync(self, job):
    #     self.logger = SyncLogging(job=job.pk)
    #     if self.status == DataSourceStatusChoices.SYNCING:
    #         self.logger.log_failure(
    #             "Cannot initiate sync; syncing already in progress.", obj=self
    #         )
    #         raise SyncError("Cannot initiate sync; syncing already in progress.")
    #
    #     pre_sync.send(sender=self.__class__, instance=self)
    #
    #     self.status = DataSourceStatusChoices.SYNCING
    #     IPFabricSource.objects.filter(pk=self.pk).update(status=self.status)
    #
    #     # Begin Sync
    #     try:
    #         self.logger.log_info(f"Syncing snapshots from {self.name}", obj=self)
    #         logger.debug(f"Syncing snapshots from {self.url}")
    #
    #         self.parameters["base_url"] = self.url
    #         ipf = self.get_client(parameters=self.parameters)
    #
    #         if not ipf:
    #             raise SyncError("Unable to connect to IP Fabric.")
    #
    #         for snapshot_id, value in ipf.snapshots.items():
    #             if snapshot_id not in ["$prev", "$lastLocked"]:
    #                 if value.name:
    #                     name = (
    #                         value.name
    #                         + " - "
    #                         + value.start.strftime("%d-%b-%y %H:%M:%S")
    #                     )
    #                 else:
    #                     name = value.start.strftime("%d-%b-%y %H:%M:%S")
    #
    #                 if value.status == "done":
    #                     status = "loaded"
    #                 else:
    #                     status = value.status
    #
    #                 data = {
    #                     "source": self,
    #                     "name": name,
    #                     "data": json.loads(value.json()),
    #                     "date": value.start,
    #                     "created": timezone.now(),
    #                     "last_updated": timezone.now(),
    #                     "status": status,
    #                 }
    #                 snapshot, _ = IPFabricSnapshot.objects.update_or_create(
    #                     snapshot_id=snapshot_id, defaults=data
    #                 )
    #                 self.logger.log_info(
    #                     f"Created/Updated Snapshot {snapshot.name} ({snapshot.snapshot_id})",
    #                     obj=snapshot,
    #                 )
    #         self.status = DataSourceStatusChoices.COMPLETED
    #         self.logger.log_success(f"Completed syncing snapshots from {self.name}")
    #         logger.debug(f"Completed syncing snapshots from {self.url}")
    #     except Exception as e:
    #         self.handle_sync_failure(type(e).__name__, e)
    #     finally:
    #         self.last_synced = timezone.now()
    #         IPFabricSource.objects.filter(pk=self.pk).update(
    #             status=self.status, last_synced=self.last_synced
    #         )
    #         self.logger.log_info("Sync job completed.", obj=self)
    #         if job:
    #             job.data = self.logger.log_data
    #     # Emit the post_sync signal
    #     # post_sync.send(sender=self.__class__, instance=self)
