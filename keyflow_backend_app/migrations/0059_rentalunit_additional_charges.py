# Generated by Django 4.2.4 on 2024-01-17 15:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0058_rentalunit_template_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalunit',
            name='additional_charges',
            field=models.TextField(blank=True, default='[]', null=True),
        ),
    ]
