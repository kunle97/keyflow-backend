from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User 
from keyflow_backend_app.models.rental_property import RentalProperty 
from keyflow_backend_app.models.rental_unit import RentalUnit
from keyflow_backend_app.models.lease_agreement import LeaseAgreement
    
class LeaseCancellationRequest(models.Model):
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None)#tenant that created the lease cancellation request
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #land lord the lease cancellation request is for
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    lease_agreement = models.ForeignKey(LeaseAgreement, on_delete=models.CASCADE, default=None)
    request_date = models.DateTimeField()
    is_approved = models.BooleanField(default=False)
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None)
    comments = models.TextField()
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'lease_cancellation_requests'

    def __str__(self):
        return f"Cancellation Request for {self.tenant} on Unit {self.unit}"
