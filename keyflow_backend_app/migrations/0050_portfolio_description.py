# Generated by Django 4.2.4 on 2024-01-07 15:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0049_transaction_tenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfolio',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]