# Generated by Django 4.2.4 on 2024-01-09 21:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0052_alter_leaseagreement_tenant_alter_transaction_tenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='leasetemplate',
            name='rent_frequency',
            field=models.CharField(default='', max_length=100),
        ),
    ]
