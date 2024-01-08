# Generated by Django 4.2.4 on 2024-01-08 15:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0051_alter_rentalproperty_portfolio'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leaseagreement',
            name='tenant',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lease_agreements', to='keyflow_backend_app.tenant'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='tenant',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='keyflow_backend_app.tenant'),
        ),
    ]