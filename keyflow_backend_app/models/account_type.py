from enum import unique
from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User


class Owner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None, unique=True, blank=False, null=False)
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    date_joined = models.DateTimeField(default=datetime.now, blank=True)

    class Meta:
        db_table = "owners"

    def __str__(self):
        return f"Owner {self.user}"


class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None, unique=True, blank=False, null=False)
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    owner = models.ForeignKey(
        Owner, on_delete=models.CASCADE, default=None, related_name="owner_staff"
    )
    title = models.CharField(max_length=255, blank=True, null=True) #Custom id for the employee set by owner. Possible values: "property manager", "employee", "maintenance", "other"
    privileges = models.CharField(max_length=255, blank=True, null=True) #Tell the account what they can do to each resource type (rental unit, tenant, etc.). Possible values: "create","read", "update", "delete", "all"
    date_joined = models.DateTimeField(default=datetime.now, blank=True)

    class Meta:
        db_table = "staff"

    def __str__(self):
        return f"Staff {self.user} for {self.owner.user.first_name} and {self.owner.user.last_name}"


class Tenant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None, unique=True, blank=False, null=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    owner = models.ForeignKey(
        Owner, on_delete=models.CASCADE, default=None, related_name="owner_tenant"
    )
    date_joined = models.DateTimeField(default=datetime.now, blank=True)

    class Meta:
        db_table = "tenants"

    def __str__(self):
        return f"Tenant {self.user}"
    

class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None, unique=True, blank=True, null=True)
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    date_joined = models.DateTimeField(default=datetime.now, blank=True)

    class Meta:
        db_table = "vendors"

    def __str__(self):
        return f"Vendor {self.user}"
