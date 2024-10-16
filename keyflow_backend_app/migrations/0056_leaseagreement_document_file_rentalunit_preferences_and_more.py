# Generated by Django 4.2.4 on 2024-01-16 15:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0055_tenantinvite'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaseagreement',
            name='document_file',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='keyflow_backend_app.uploadedfile'),
        ),
        migrations.AddField(
            model_name='rentalunit',
            name='preferences',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rentalunit',
            name='stripe_price_id',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='rentalunit',
            name='stripe_product_id',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='tenantinvite',
            name='approval_hash',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
