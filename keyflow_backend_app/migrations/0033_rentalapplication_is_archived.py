# Generated by Django 4.2.4 on 2023-08-29 02:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0032_leaseagreement_created_at_leaseagreement_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalapplication',
            name='is_archived',
            field=models.BooleanField(default=False),
        ),
    ]