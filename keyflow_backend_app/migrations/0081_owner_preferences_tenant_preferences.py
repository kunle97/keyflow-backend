# Generated by Django 4.2.4 on 2024-04-18 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0080_alter_expiringtoken_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='owner',
            name='preferences',
            field=models.TextField(blank=True, default='\n[\n    {\n        "name": "tenant_lease_agreement_signed",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "lease_cancellation_request_created",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "lease_renewal_request_created",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "lease_renewal_agreement_signed",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "rental_application_created",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "invoice_paid",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "new_tenant_registration_complete",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    }\n]\n', null=True),
        ),
        migrations.AddField(
            model_name='tenant',
            name='preferences',
            field=models.TextField(blank=True, default='\n[\n    {\n        "name": "lease_cancellation_request_approved",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "lease_cancellation_request_denied",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "lease_renewal_request_approved",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "lease_renewal_request_rejected",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    },\n    {\n        "name": "bill_created",\n        "values": [\n            {"name": "push", "value": false},\n            {"name": "email", "value": false}\n        ]\n    }\n]\n', null=True),
        ),
    ]
