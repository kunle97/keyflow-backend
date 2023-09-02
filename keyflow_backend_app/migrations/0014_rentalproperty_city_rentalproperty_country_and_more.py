# Generated by Django 4.2.4 on 2023-08-19 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0013_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalproperty',
            name='city',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='rentalproperty',
            name='country',
            field=models.CharField(default='United States', max_length=100),
        ),
        migrations.AddField(
            model_name='rentalproperty',
            name='state',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='rentalproperty',
            name='zip_code',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]