# Generated by Django 4.2.4 on 2024-06-13 18:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0102_alter_portfolio_preferences_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintenancerequest',
            name='billing_entry',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='keyflow_backend_app.billingentry'),
        ),
    ]