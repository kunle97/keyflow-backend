# Generated by Django 4.2.4 on 2023-11-29 02:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0021_remove_message_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='file',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='keyflow_backend_app.uploadedfile'),
        ),
    ]
