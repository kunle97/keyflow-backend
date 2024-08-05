# Generated by Django 4.2.4 on 2024-04-23 23:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0083_alter_owner_preferences_alter_tenant_preferences'),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to='keyflow_backend_app.owner')),
                ('portfolio', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to='keyflow_backend_app.portfolio')),
                ('rental_property', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to='keyflow_backend_app.rentalproperty')),
                ('rental_unit', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to='keyflow_backend_app.rentalunit')),
            ],
            options={
                'db_table': 'announcements',
            },
        ),
    ]
