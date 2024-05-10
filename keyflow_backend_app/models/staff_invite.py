from django.db import models
from keyflow_backend_app.models.account_type import Owner, Staff

class StaffInvite(models.Model):#Keeps track of when owners invite tenants to a rental unit. Useful for when they onboard onto the platform with existing tenants
    first_name = models.CharField(max_length=100, blank=False, null=False, default=None)
    last_name = models.CharField(max_length=100, blank=False, null=False, default=None)
    email = models.EmailField(max_length=100, blank=False, null=False, default=None)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, default=None, blank=True, null=True)
    approval_hash = models.CharField(max_length=100, blank=True, null=True,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_invites'
    def __str__(self):
        return f"Staff invite from {self.owner} to {self.first_name} {self.last_name}"