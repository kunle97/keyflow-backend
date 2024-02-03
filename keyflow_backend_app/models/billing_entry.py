from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Tenant,Owner
from keyflow_backend_app.models.user import User
from keyflow_backend_app.models.rental_unit import RentalUnit 
from keyflow_backend_app.models.rental_property import RentalProperty

class BillingEntry(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    description = models.TextField()
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, default=None, blank=True, null=True, related_name='billing_entries')
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None, related_name='billing_entries')
    description = models.TextField()
    due_date = models.DateTimeField(default=None,  blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'billing_entries'

    def __str__(self):
        return f"Billing Entry for {self.owner.user.first_name} {self.owner.user.last_name} on {self.created_at} for the amount of {self.amount}"