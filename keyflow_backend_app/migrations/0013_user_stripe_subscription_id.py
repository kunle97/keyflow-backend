# Generated by Django 4.2.4 on 2023-11-20 03:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0012_uploadedfile_subfolder'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='stripe_subscription_id',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
    ]