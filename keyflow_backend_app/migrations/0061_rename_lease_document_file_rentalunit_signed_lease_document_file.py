# Generated by Django 4.2.4 on 2024-01-18 13:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0060_rentalunit_lease_document_file'),
    ]

    operations = [
        migrations.RenameField(
            model_name='rentalunit',
            old_name='lease_document_file',
            new_name='signed_lease_document_file',
        ),
    ]
