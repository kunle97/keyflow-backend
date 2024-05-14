from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner,Tenant
from keyflow_backend_app.models.rental_property import RentalProperty
from keyflow_backend_app.models.uploaded_file import UploadedFile


default_rental_unit_preferences = """
[
    {
        "type": "unit_preferences",
        "hidden": false,
        "label": "Accept Rental Applications",
        "name": "accept_rental_applications",
        "inputType": "switch",
        "value": true,
        "description": "Indicates if the owner is accepting rental applications for this unit"
    },
    {
        "type": "unit_preferences",
        "hidden": false,
        "label": "Acccept Lease Renewals",
        "name": "accept_lease_renewals",
        "inputType": "switch",
        "value": true,
        "description": "Indicates if the owner is accepting lease renewals for this unit"
    },
    {
        "type": "unit_preferences",
        "hidden": false,
        "label": "Accept Lease Cancellations",
        "name": "accept_lease_cancellations",
        "inputType": "switch",
        "value": true,
        "description": "Indicates if the owner is accepting lease cancellations for this unit"
    }
]
"""


class RentalUnit(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None) #Owner of the unit
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, default=None, related_name='tenant_unit', blank=True, null=True) #Tenant of the unit
    name = models.CharField(max_length=100, blank=True)
    beds = models.PositiveIntegerField()
    baths = models.PositiveIntegerField()
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE, related_name='rental_units')
    size = models.PositiveIntegerField(default=0)
    lease_template = models.ForeignKey('LeaseTemplate', on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='rental_units')
    template_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    signed_lease_document_file = models.ForeignKey(UploadedFile, on_delete=models.SET_NULL, blank=True, null=True, default=None, related_name='rental_units')
    signed_lease_document_metadata = models.TextField(blank=True, null=True, default="[]") #JSON string of signed lease metadata
    lease_terms = models.TextField(blank=True, null=True, default='[{"name":"rent","label":"Rent","value":1500,"inputType":"number","description":"How much you are going to charge for rent per period","type":"lease"},{"name":"rent_frequency","label":"Rent Frequency","inputType":"select","options":[{"value":"day","label":"Daily"},{"value":"month","label":"Monthly"},{"value":"week","label":"Weekly"},{"value":"year","label":"Yearly"}],"value":"month","description":"How often you are going to charge rent. This can be daily, monthly, weekly, or yearly","type":"lease"},{"name":"term","label":"Term","inputType":"number","value":12,"description":"How long the lease is for in the selected rent frequency","type":"lease"},{"name":"late_fee","label":"Late Fee","inputType":"number","value":100,"description":"How much you will charge for late rent payments","type":"lease"},{"name":"security_deposit","label":"Security Deposit","inputType":"number","value":100,"description":"How much the tenant will pay for a security deposit. This will be returned to them at the end of the lease if all conditions are met","type":"lease"},{"name":"gas_included","label":"Include Gas Bill In Rent","inputType":"switch","value":true,"description":"Indicates if gas bill is included in the rent","type":"lease"},{"name":"electricity_included","label":"Include Electricity Bill In Rent","inputType":"switch","value":true,"description":"Indicates if electricity bill is included in the rent","type":"lease"},{"name":"water_included","label":"Include Water Bill In Rent","inputType":"switch","value":true,"description":"Indicates if water bill is included in the rent","type":"lease"},{"name":"repairs_included","label":"Include Repairs In Rent","inputType":"switch","value":true,"description":"Indicates if repairs are included in the rent. If not, the tenant will be responsible for all repair bills","type":"lease"},{"name":"grace_period","label":"Grace Period","inputType":"number","value":0,"description":"How many days before the first rent payment is due","type":"lease"},{"name":"lease_cancellation_notice_period","label":"Lease Cancellation Notice Period","inputType":"number","value":0,"description":"How many months a tenant must wait before the end of the lease to cancel the lease","type":"lease"},{"name":"lease_cancellation_fee","label":"Lease Cancellation Fee","inputType":"number","value":0,"description":"How much the tenant must pay to cancel the lease before the end of the lease","type":"lease"},{"name":"lease_renewal_notice_period","label":"Lease Renewal Notice Period","inputType":"number","value":0,"description":"How many months before the end of the lease the tenant must notify the owner of their intent to renew the lease","type":"lease"},{"name":"lease_renewal_fee","label":"Lease Renewal Fee","inputType":"number","value":0,"description":"How much the tenant must pay to renew the lease","type":"lease"}]') #JSON string of unit preferences
    additional_charges = models.TextField(blank=True, null=True, default="[]") #JSON string of additional charges
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    is_occupied = models.BooleanField(default=False)
    preferences = models.TextField(blank=True, null=True, default=default_rental_unit_preferences) #JSON string of unit preferences
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'rental_units'

    def __str__(self):
        return f"Unit {self.name} at {self.rental_property.street}"
    