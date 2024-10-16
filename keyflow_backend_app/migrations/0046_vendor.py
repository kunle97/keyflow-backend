# Generated by Django 4.2.4 on 2023-12-29 00:14

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0045_rename_created_at_transaction_timestamp_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_account_id', models.CharField(blank=True, max_length=255, null=True)),
                ('date_joined', models.DateTimeField(blank=True, default=datetime.datetime.now)),
                ('user', models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'vendors',
            },
        ),
    ]
