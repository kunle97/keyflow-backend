# Generated by Django 4.2.4 on 2024-02-23 21:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0076_alter_rentalunit_lease_terms'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaserenewalrequest',
            name='rent_frequency',
            field=models.CharField(default=None, max_length=255, null=True),
        ),
    ]
