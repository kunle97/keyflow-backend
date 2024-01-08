# Generated by Django 4.2.4 on 2024-01-07 19:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0050_portfolio_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rentalproperty',
            name='portfolio',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rental_properties', to='keyflow_backend_app.portfolio'),
        ),
    ]