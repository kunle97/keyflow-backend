# Generated by Django 4.2.4 on 2023-11-29 02:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0020_message_file'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='file',
        ),
    ]
