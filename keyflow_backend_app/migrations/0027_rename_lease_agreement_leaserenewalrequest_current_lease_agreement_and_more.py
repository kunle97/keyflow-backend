# Generated by Django 4.2.4 on 2023-12-13 13:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0026_leaserenewalrequest'),
    ]

    operations = [
        migrations.RenameField(
            model_name='leaserenewalrequest',
            old_name='lease_agreement',
            new_name='current_lease_agreement',
        ),
        migrations.AddField(
            model_name='leaserenewalrequest',
            name='new_lease_agreement',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='new_lease_agreement', to='keyflow_backend_app.leaseagreement'),
        ),
    ]