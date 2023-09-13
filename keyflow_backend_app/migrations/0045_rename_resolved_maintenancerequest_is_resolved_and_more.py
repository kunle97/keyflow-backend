# Generated by Django 4.2.4 on 2023-09-04 21:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0044_rename_user_maintenancerequest_tenant'),
    ]

    operations = [
        migrations.RenameField(
            model_name='maintenancerequest',
            old_name='resolved',
            new_name='is_resolved',
        ),
        migrations.AddField(
            model_name='maintenancerequest',
            name='is_archived',
            field=models.BooleanField(default=False),
        ),
    ]
