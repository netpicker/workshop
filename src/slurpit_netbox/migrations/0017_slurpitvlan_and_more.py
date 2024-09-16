# Generated by Django 5.0.6 on 2024-08-13 09:07

import django.core.validators
import django.db.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0187_alter_device_vc_position"),
        ("extras", "0115_convert_dashboard_widgets"),
        ("ipam", "0069_gfk_indexes"),
        ("slurpit_netbox", "0016_slurpitprefix_ignore_description_and_more"),
        ("tenancy", "0015_contactassignment_rename_content_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="SlurpitVLAN",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "custom_field_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=utilities.json.CustomFieldJSONEncoder,
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=200)),
                ("comments", models.TextField(blank=True)),
                (
                    "vid",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(4094),
                        ]
                    ),
                ),
                ("name", models.CharField(max_length=64)),
                ("status", models.CharField(default="active", max_length=50)),
                ("enable_reconcile", models.BooleanField(default=False)),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="slurpit_vlans",
                        to="ipam.vlangroup",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="slurpit_vlans",
                        to="ipam.role",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="slurpit_vlans",
                        to="dcim.site",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        through="extras.TaggedItem", to="extras.Tag"
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="slurpit_vlans",
                        to="tenancy.tenant",
                    ),
                ),
            ],
            options={
                "verbose_name": "VLAN",
                "verbose_name_plural": "VLANs",
                "ordering": ("site", "group", "vid", "pk"),
            },
        ),
        migrations.AddConstraint(
            model_name="slurpitvlan",
            constraint=models.UniqueConstraint(
                fields=("group", "vid"),
                name="slurpit_netbox_slurpitvlan_unique_group_vid",
            ),
        ),
        migrations.AddConstraint(
            model_name="slurpitvlan",
            constraint=models.UniqueConstraint(
                fields=("group", "name"),
                name="slurpit_netbox_slurpitvlan_unique_group_name",
            ),
        ),
    ]