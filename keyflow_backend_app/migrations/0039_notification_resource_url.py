# Generated by Django 4.2.4 on 2023-12-26 15:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0038_remove_leaserenewalrequest_new_lease_agreement_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='resource_url',
            field=models.TextField(blank=True, default='/', null=True),
        ),
    ]