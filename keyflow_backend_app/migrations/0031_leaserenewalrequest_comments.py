# Generated by Django 4.2.4 on 2023-12-16 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0030_leaserenewalrequest_move_in_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaserenewalrequest',
            name='comments',
            field=models.TextField(blank=True, null=True),
        ),
    ]