# Generated by Django 4.2.4 on 2024-02-22 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keyflow_backend_app', '0075_maintenancerequest_priority'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rentalunit',
            name='lease_terms',
            field=models.TextField(blank=True, default='[{"name":"rent","label":"Rent","value":1500,"inputType":"number","description":"How much you are going to charge for rent per period","type":"lease"},{"name":"rent_frequency","label":"Rent Frequency","inputType":"select","options":[{"value":"day","label":"Daily"},{"value":"month","label":"Monthly"},{"value":"week","label":"Weekly"},{"value":"year","label":"Yearly"}],"value":"month","description":"How often you are going to charge rent. This can be daily, monthly, weekly, or yearly","type":"lease"},{"name":"term","label":"Term","inputType":"number","value":12,"description":"How long the lease is for in the selected rent frequency","type":"lease"},{"name":"late_fee","label":"Late Fee","inputType":"number","value":100,"description":"How much you will charge for late rent payments","type":"lease"},{"name":"security_deposit","label":"Security Deposit","inputType":"number","value":100,"description":"How much the tenant will pay for a security deposit. This will be returned to them at the end of the lease if all conditions are met","type":"lease"},{"name":"gas_included","label":"Include Gas Bill In Rent","inputType":"switch","value":true,"description":"Indicates if gas bill is included in the rent","type":"lease"},{"name":"electricity_included","label":"Include Electricity Bill In Rent","inputType":"switch","value":true,"description":"Indicates if electricity bill is included in the rent","type":"lease"},{"name":"water_included","label":"Include Water Bill In Rent","inputType":"switch","value":true,"description":"Indicates if water bill is included in the rent","type":"lease"},{"name":"repairs_included","label":"Include Repairs In Rent","inputType":"switch","value":true,"description":"Indicates if repairs are included in the rent. If not, the tenant will be responsible for all repair bills","type":"lease"},{"name":"grace_period","label":"Grace Period","inputType":"number","value":0,"description":"How many days before the first rent payment is due","type":"lease"},{"name":"lease_cancellation_notice_period","label":"Lease Cancellation Notice Period","inputType":"number","value":0,"description":"How many months a tenant must wait before the end of the lease to cancel the lease","type":"lease"},{"name":"lease_cancellation_fee","label":"Lease Cancellation Fee","inputType":"number","value":0,"description":"How much the tenant must pay to cancel the lease before the end of the lease","type":"lease"},{"name":"lease_renewal_notice_period","label":"Lease Renewal Notice Period","inputType":"number","value":0,"description":"How many months before the end of the lease the tenant must notify the landlord of their intent to renew the lease","type":"lease"},{"name":"lease_renewal_fee","label":"Lease Renewal Fee","inputType":"number","value":0,"description":"How much the tenant must pay to renew the lease","type":"lease"}]', null=True),
        ),
    ]
