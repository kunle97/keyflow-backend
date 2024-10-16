# Generated by Django 4.2.4 on 2024-01-07 15:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0048_alter_transaction_type_portfolio_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='tenant',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tenant', to='keyflow_backend_app.tenant'),
        ),
    ]
