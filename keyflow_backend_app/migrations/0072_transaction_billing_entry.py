# Generated by Django 4.2.4 on 2024-02-01 12:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0071_alter_billingentry_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='billing_entry',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='keyflow_backend_app.billingentry'),
        ),
    ]