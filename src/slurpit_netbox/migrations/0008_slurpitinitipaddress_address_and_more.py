# Generated by Django 4.2.9 on 2024-04-19 08:05

import django.core.validators
from django.db import migrations, models
import ipam.fields


class Migration(migrations.Migration):

    dependencies = [
        ('slurpit_netbox', '0007_slurpitinitipaddress'),
    ]

    operations = [
        migrations.AddField(
            model_name='slurpitinitipaddress',
            name='address',
            field=ipam.fields.IPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='slurpitinitipaddress',
            name='dns_name',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[django.core.validators.RegexValidator(code='invalid', message='Only alphanumeric characters, asterisks, hyphens, periods, and underscores are allowed in DNS names', regex='^([0-9A-Za-z_-]+|\\*)(\\.[0-9A-Za-z_-]+)*\\.?$')]),
        ),
    ]
