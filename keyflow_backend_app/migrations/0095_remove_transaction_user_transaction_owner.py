# Generated by Django 4.2.4 on 2024-05-27 16:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0094_portfolio_lease_template_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='user',
        ),
        migrations.AddField(
            model_name='transaction',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, default=None, on_delete=django.db.models.deletion.CASCADE, to='keyflow_backend_app.owner'),
        ),
    ]
