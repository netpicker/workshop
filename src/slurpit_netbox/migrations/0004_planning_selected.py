# Generated by Django 4.2.7 on 2023-12-02 12:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('slurpit_netbox', '0003_planning'),
    ]

    operations = [
        migrations.AddField(
            model_name='planning',
            name='selected',
            field=models.BooleanField(default=False),
        ),
    ]
