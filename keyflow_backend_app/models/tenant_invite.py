from django.db import models
from django.utils import timezone
from keyflow_backend_app.models.account_type import Owner, Tenant
from keyflow_backend_app.models.rental_unit import RentalUnit

class TenantInvite(models.Model):#Keeps track of when owners invite tenants to a rental unit. Useful for when they onboard onto the platform with existing tenants
    first_name = models.CharField(max_length=100, blank=False, null=False, default=None)
    last_name = models.CharField(max_length=100, blank=False, null=False, default=None)
    email = models.EmailField(max_length=100, blank=False, null=False, default=None, unique=True)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, default=None, blank=True, null=True)
    approval_hash = models.CharField(max_length=100, blank=True, null=True,unique=True)
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE, default=None, unique=True)
    last_sent_at = models.DateTimeField(null=True, blank=True, default=timezone.now) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tenant_invites'
    def __str__(self):
        return f"Invite from {self.owner} to {self.tenant} for {self.rental_unit}"