# Generated by Django 4.2.4 on 2024-04-25 22:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0086_rename_delivery_date_announcement_start_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='severity',
            field=models.CharField(default='info', max_length=255),
        ),
    ]