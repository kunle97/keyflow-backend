# Generated by Django 4.2.4 on 2023-11-24 21:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0016_alter_uploadedfile_file_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadedfile',
            name='file_key',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]
