# Generated by Django 4.2.4 on 2023-12-16 15:54

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0032_leaserenewalrequest_rental_property'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaserenewalrequest',
            name='created_at',
            field=models.DateTimeField(blank=True, default=datetime.datetime.now),
        ),
        migrations.AddField(
            model_name='leaserenewalrequest',
            name='date_approved',
            field=models.DateTimeField(default=None, null=True),
        ),
    ]