from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner

class LeaseTemplate(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None) #Owner that created the lease term
    rent = models.DecimalField(max_digits=10, decimal_places=2)
    rent_frequency = models.CharField(max_length=100, blank=False, null=False, default="") #Frequency of rent payments
    term = models.IntegerField() #Integer for duration of lease in months
    template_id = models.CharField(max_length=100, blank=False, null=False, default="") #BoldSign template ID
    description = models.TextField() #descriptionn of the property and lease template id (to be displayed on REntal App page)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    gas_included = models.BooleanField(default=False)
    water_included = models.BooleanField(default=False)
    electric_included = models.BooleanField(default=False)
    repairs_included = models.BooleanField(default=False)
    additional_charges =  models.TextField(blank=True, null=True, default="[]") #Additional charges to be displayed on Rental App page
    grace_period = models.IntegerField(default=0) #Integer for time until user must pay first rent payment period in months
    lease_cancellation_notice_period = models.IntegerField() #Integer for notice period in months
    lease_cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    lease_renewal_notice_period = models.IntegerField(default=None, null=True) #Integer for notice period in months
    lease_renewal_fee = models.DecimalField(max_digits=10, decimal_places=2, default=None, null=True)
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'lease_templates'

    def __str__(self):
       return f"Lease Template for {self.term} months"
