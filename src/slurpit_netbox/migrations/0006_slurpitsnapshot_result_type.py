# Generated by Django 4.2.9 on 2024-04-08 13:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('slurpit_netbox', '0005_manufacturer'),
    ]

    operations = [
        migrations.AddField(
            model_name='slurpitsnapshot',
            name='result_type',
            field=models.CharField(default='template_result', max_length=255),
        ),
    ]