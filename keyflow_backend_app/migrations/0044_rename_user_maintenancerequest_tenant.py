# Generated by Django 4.2.4 on 2023-09-04 21:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0043_alter_rentalproperty_zip_code'),
    ]

    operations = [
        migrations.RenameField(
            model_name='maintenancerequest',
            old_name='user',
            new_name='tenant',
        ),
    ]
