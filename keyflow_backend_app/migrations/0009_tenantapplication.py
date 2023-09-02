# Generated by Django 4.2.4 on 2023-08-11 22:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0008_leasecancellationrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='TenantApplication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone_number', models.CharField(max_length=15)),
                ('desired_move_in_date', models.DateField()),
                ('additional_comments', models.TextField(blank=True, null=True)),
                ('is_approved', models.BooleanField(default=False)),
                ('paystubs', models.FileField(blank=True, null=True, upload_to='tenant_paystubs/')),
                ('bank_statements', models.FileField(blank=True, null=True, upload_to='tenant_bank_statements/')),
                ('references', models.TextField(blank=True, null=True)),
                ('landlord', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tenant_applications', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]