# Generated by Django 4.2.4 on 2023-11-23 18:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0014_alter_leasetemplate_additional_charges'),
    ]

    operations = [
        migrations.AlterField(
            model_name='maintenancerequest',
            name='type',
            field=models.CharField(choices=[('plumbing', 'Plumbling'), ('electrical', 'Electrical'), ('appliance', 'Appliance'), ('structural', 'Structural'), ('hvac', 'HVAC'), ('other', 'Other')], max_length=35),
        ),
    ]
