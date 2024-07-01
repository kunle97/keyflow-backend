from email.policy import default
from django.db import models
from datetime import datetime
from keyflow_backend_app.models.account_type import Owner,Tenant
from keyflow_backend_app.models.rental_unit import RentalUnit
from keyflow_backend_app.models.rental_property import RentalProperty

class LeaseRenewalRequest(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, default=None, related_name='renewal_requests_as_tenant')
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None, related_name='renewal_requests_as_user')
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE, default=None)
    renewal_date = models.DateTimeField(default=None, null=True) #Date of renewal approval by owner
    move_in_date = models.DateTimeField(default=None, null=True) #Date of move in for new lease
    request_date = models.DateTimeField() #Date of request created by tenant
    request_term = models.IntegerField(default=None, null=True) #Integer for duration of lease in the same frequency as the rental unit
    rent_frequency = models.CharField(max_length=255, default=None, null=True) #Month, Week, Year, day
    status = models.CharField(max_length=255, default='pending') # pending, approved, denied
    comments = models.TextField(blank=True, null=True)
    #Created a feild to keep track of the date the request was submitted
    created_at = models.DateTimeField(default=datetime.now, blank=True)

    class Meta:
        db_table = 'lease_renewal_requests'
    def __str__(self):
        return f"Renewal Request for {self.tenant} on Unit {self.rental_unit}"