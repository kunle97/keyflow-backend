# Generated by Django 4.2.4 on 2024-04-12 15:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0079_expiringtoken'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='expiringtoken',
            table='expiring_tokens',
        ),
    ]
