# Generated by Django 4.2.4 on 2023-12-16 18:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0033_leaserenewalrequest_created_at_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='leaserenewalrequest',
            name='date_approved',
        ),
    ]