# Generated by Django 4.2.4 on 2024-06-13 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0101_alter_tenant_auto_renew_lease_is_enabled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portfolio',
            name='preferences',
            field=models.TextField(blank=True, default='\n    [\n        {\n            "type": "portfolio_preferences",\n            "hidden": false,\n            "label": "Accept Rental Applications",\n            "name": "accept_rental_applications",\n            "inputType": "switch",\n            "value": true,\n            "description": "Indicates if the owner is accepting rental applications for this portfolio"\n        },\n        {\n            "type": "portfolio_preferences",\n            "hidden": false,\n            "label": "Acccept Lease Renewals",\n            "name": "accept_lease_renewals",\n            "inputType": "switch",\n            "value": true,\n            "description": "Indicates if the owner is accepting lease renewals for this portfolio"\n        },\n        {\n            "type": "portfolio_preferences",\n            "hidden": false,\n            "label": "Accept Lease Cancellations",\n            "name": "accept_lease_cancellations",\n            "inputType": "switch",\n            "value": true,\n            "description": "Indicates if the owner is accepting lease cancellations for this portfolio"\n        },\n        {\n            "type": "unit_preferences",\n            "hidden": false,\n            "label": "Allow Lease Auto Renewal",\n            "name": "allow_lease_auto_renewal",\n            "inputType": "switch",\n            "value": true,\n            "description": "Indicates if the owner is allowing tenants in subsequent units to enable auto renewal of their lease"\n        }\n    ]\n    ', null=True),
        ),
        migrations.AlterField(
            model_name='rentalproperty',
            name='preferences',
            field=models.TextField(blank=True, default='\n[\n    {\n        "type": "property_preferences",\n        "hidden": false,\n        "label": "Accept Rental Applications",\n        "name": "accept_rental_applications",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the owner is accepting rental applications for this property"\n    },\n    {\n        "type": "property_preferences",\n        "hidden": false,\n        "label": "Acccept Lease Renewals",\n        "name": "accept_lease_renewals",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the owner is accepting lease renewals for this property"\n    },\n    {\n        "type": "property_preferences",\n        "hidden": false,\n        "label": "Accept Lease Cancellations",\n        "name": "accept_lease_cancellations",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the owner is accepting lease cancellations for this property"\n    },\n    {\n        "type": "unit_preferences",\n        "hidden": false,\n        "label": "Allow Lease Auto Renewal",\n        "name": "allow_lease_auto_renewal",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the owner is allowing tenants in subsequent units to enable auto renewal of their lease"\n    }\n]\n', null=True),
        ),
        migrations.AlterField(
            model_name='rentalunit',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='rentalunit',
            name='preferences',
            field=models.TextField(blank=True, default='\n[\n    {\n        "type": "unit_preferences",\n        "hidden": false,\n        "label": "Accept Rental Applications",\n        "name": "accept_rental_applications",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the owner is accepting rental applications for this unit"\n    },\n    {\n        "type": "unit_preferences",\n        "hidden": false,\n        "label": "Acccept Lease Renewals",\n        "name": "accept_lease_renewals",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the owner is accepting lease renewals for this unit"\n    },\n    {\n        "type": "unit_preferences",\n        "hidden": false,\n        "label": "Accept Lease Cancellations",\n        "name": "accept_lease_cancellations",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the owner is accepting lease cancellations for this unit"\n    },\n    {\n        "type": "unit_preferences",\n        "hidden": false,\n        "label": "Allow Lease Auto Renewal",\n        "name": "allow_lease_auto_renewal",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the owner is allowing tenants in this unit to enable auto renewal of their lease"\n    }\n]\n', null=True),
        ),
    ]
