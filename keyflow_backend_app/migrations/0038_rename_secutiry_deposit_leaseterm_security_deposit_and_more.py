# Generated by Django 4.2.4 on 2023-08-30 22:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0037_leaseterm_user'),
    ]

    operations = [
        migrations.RenameField(
            model_name='leaseterm',
            old_name='secutiry_deposit',
            new_name='security_deposit',
        ),
        migrations.AddField(
            model_name='leaseterm',
            name='unit',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='keyflow_backend_app.rentalunit'),
        ),
    ]