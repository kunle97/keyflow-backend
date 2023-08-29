# Generated by Django 4.2.4 on 2023-08-29 03:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0034_remove_leaseagreement_rental_property_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leaseagreement',
            name='tenant',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tenant', to=settings.AUTH_USER_MODEL),
        ),
    ]
