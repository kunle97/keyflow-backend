# Generated by Django 4.2.4 on 2023-08-28 21:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0030_rentalapplication_date_of_birth'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalunit',
            name='is_occupied',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='leaseagreement',
            name='approval_hash',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='rentalapplication',
            name='approval_hash',
            field=models.CharField(blank=True, default=None, max_length=100, null=True, unique=True),
        ),
    ]
