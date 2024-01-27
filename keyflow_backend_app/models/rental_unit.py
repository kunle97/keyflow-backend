from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner,Tenant
from keyflow_backend_app.models.rental_property import RentalProperty
from keyflow_backend_app.models.uploaded_file import UploadedFile

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
    lease_terms = models.TextField(blank=True, null=True, default="[]") #JSON string of unit preferences
    additional_charges = models.TextField(blank=True, null=True, default="[]") #JSON string of additional charges
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    is_occupied = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'rental_units'

    def __str__(self):
        return f"Unit {self.name} at {self.rental_property.street}"
    