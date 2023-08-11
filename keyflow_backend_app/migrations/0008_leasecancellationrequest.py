# Generated by Django 4.2.4 on 2023-08-11 02:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0007_leaseagreement_tenant'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaseCancellationRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_date', models.DateTimeField()),
                ('is_approved', models.BooleanField(default=False)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='keyflow_backend_app.rentalproperty')),
            ],
        ),
    ]
