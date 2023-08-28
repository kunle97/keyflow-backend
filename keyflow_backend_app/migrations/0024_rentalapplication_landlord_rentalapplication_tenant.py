# Generated by Django 4.2.4 on 2023-08-27 14:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0023_alter_rentalapplication_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalapplication',
            name='landlord',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='tenant_application_landlord', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='rentalapplication',
            name='tenant',
            field=models.ForeignKey(blank=True, default=None, on_delete=django.db.models.deletion.CASCADE, related_name='tenant_application_tenant', to=settings.AUTH_USER_MODEL),
        ),
    ]
