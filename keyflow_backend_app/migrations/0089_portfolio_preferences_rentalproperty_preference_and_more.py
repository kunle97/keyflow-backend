# Generated by Django 4.2.4 on 2024-04-27 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0088_remove_announcement_portfolio_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfolio',
            name='preferences',
            field=models.TextField(blank=True, default='\n    [\n        {\n            "type": "portfolio_preferences",\n            "hidden": false,\n            "label": "Accept Rental Applications",\n            "name": "accept_rental_applications",\n            "inputType": "switch",\n            "value": true,\n            "description": "Indicates if the landlord is accepting rental applications for this portfolio"\n        },\n        {\n            "type": "portfolio_preferences",\n            "hidden": false,\n            "label": "Acccept Lease Renewals",\n            "name": "accept_lease_renewals",\n            "inputType": "switch",\n            "value": true,\n            "description": "Indicates if the landlord is accepting lease renewals for this portfolio"\n        },\n        {\n            "type": "portfolio_preferences",\n            "hidden": false,\n            "label": "Accept Lease Cancellations",\n            "name": "accept_lease_cancellations",\n            "inputType": "switch",\n            "value": true,\n            "description": "Indicates if the landlord is accepting lease cancellations for this portfolio"\n        }\n    ]\n    ', null=True),
        ),
        migrations.AddField(
            model_name='rentalproperty',
            name='preference',
            field=models.TextField(blank=True, default='\n[\n    {\n        "type": "property_preferences",\n        "hidden": false,\n        "label": "Accept Rental Applications",\n        "name": "accept_rental_applications",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the landlord is accepting rental applications for this property"\n    },\n    {\n        "type": "property_preferences",\n        "hidden": false,\n        "label": "Acccept Lease Renewals",\n        "name": "accept_lease_renewals",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the landlord is accepting lease renewals for this property"\n    },\n    {\n        "type": "property_preferences",\n        "hidden": false,\n        "label": "Accept Lease Cancellations",\n        "name": "accept_lease_cancellations",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the landlord is accepting lease cancellations for this property"\n    }\n]\n', null=True),
        ),
        migrations.AddField(
            model_name='rentalunit',
            name='preferences',
            field=models.TextField(blank=True, default='\n[\n    {\n        "type": "unit_preferences",\n        "hidden": false,\n        "label": "Accept Rental Applications",\n        "name": "accept_rental_applications",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the landlord is accepting rental applications for this unit"\n    },\n    {\n        "type": "unit_preferences",\n        "hidden": false,\n        "label": "Acccept Lease Renewals",\n        "name": "accept_lease_renewals",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the landlord is accepting lease renewals for this unit"\n    },\n    {\n        "type": "unit_preferences",\n        "hidden": false,\n        "label": "Accept Lease Cancellations",\n        "name": "accept_lease_cancellations",\n        "inputType": "switch",\n        "value": true,\n        "description": "Indicates if the landlord is accepting lease cancellations for this unit"\n    }\n]\n', null=True),
        ),
    ]
