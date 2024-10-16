# Generated by Django 4.2.4 on 2023-11-19 15:30

from django.db import migrations, models
import keyflow_backend_app.models.uploaded_file


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0009_alter_uploadedfile_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadedfile',
            name='file',
            field=models.FileField(max_length=255, upload_to=keyflow_backend_app.models.uploaded_file.user_directory_path),
        ),
    ]
