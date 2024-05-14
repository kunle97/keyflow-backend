from django.db import models
from datetime import datetime
from keyflow_backend_app.models.tenant_invite import TenantInvite
from keyflow_backend_app.models.account_type import Owner,Tenant
from keyflow_backend_app.models.rental_unit import RentalUnit
from keyflow_backend_app.models.rental_application import RentalApplication
from keyflow_backend_app.models.lease_template import LeaseTemplate
from keyflow_backend_app.models.lease_renewal_request import LeaseRenewalRequest
from keyflow_backend_app.models.uploaded_file import UploadedFile

class LeaseAgreement(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, default=None, blank=True, null=True, related_name='lease_agreements')
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None, related_name='owner') #Owner that created the lease agreement
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    rental_application = models.ForeignKey(RentalApplication, on_delete=models.CASCADE, default=None, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    document_id = models.CharField(max_length=100, blank=True, null=True)
    signed_lease_document_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, blank=True, null=True, default=None, related_name='lease_agreements') 
    lease_template = models.ForeignKey(LeaseTemplate, on_delete=models.CASCADE, blank=True, null=True, default=None)
    lease_renewal_request = models.ForeignKey(LeaseRenewalRequest, on_delete=models.CASCADE, blank=True, null=True, default=None)
    signed_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=False,blank=True, null=True)
    is_tenant_invite = models.BooleanField(default=False,blank=True, null=True)#Delete this field
    tenant_invite   = models.ForeignKey(TenantInvite, on_delete=models.CASCADE, default=None, blank=True, null=True)
    approval_hash = models.CharField(max_length=100, blank=True, null=True,unique=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    auto_pay_is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'lease_agreements'

    def __str__(self):
        return f"Lease Agreement for RentalUnit {self.rental_unit} "
