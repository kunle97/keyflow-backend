# Generated by Django 4.2.4 on 2023-12-19 13:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0036_leaserenewalrequest_request_term'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='leaserenewalrequest',
            name='current_lease_agreement',
        ),
    ]
