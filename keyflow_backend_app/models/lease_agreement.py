from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User

class LeaseAgreement(models.Model):
    rental_unit = models.ForeignKey('RentalUnit', on_delete=models.CASCADE)
    rental_application = models.ForeignKey('RentalApplication', on_delete=models.CASCADE, default=None)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    document_id = models.CharField(max_length=100, blank=True, null=True)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True, related_name='tenant')
    lease_term = models.ForeignKey('LeaseTerm', on_delete=models.CASCADE, blank=True, null=True, default=None)
    signed_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=False,blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='landlord') #Landlord that created the lease agreement
    approval_hash = models.CharField(max_length=100, blank=True, null=True,unique=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    auto_pay_is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'lease_agreements'

    def __str__(self):
        return f"Lease Agreement for RentalUnit {self.rental_unit} "
