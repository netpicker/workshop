# Generated by Django 5.0.6 on 2024-08-16 02:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("slurpit_netbox", "0018_slurpitvlan_ignore_description_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="slurpitvlan",
            name="name",
            field=models.CharField(blank=True, default="", max_length=64, null=True),
        ),
    ]
