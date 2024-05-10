from enum import unique
from django.db import models
from datetime import datetime
from keyflow_backend_app.models.user import User

default_owner_preferences_json = """
[
    {
        "type": "notifications",
        "hidden": false,
        "name": "tenant_lease_agreement_signed",
        "label": "Tenant Lease Agreement Signed",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable  or disable notifications for when a tenant signs a lease agreement"
    },
    {
        "type": "notifications",
        "hidden": false,
        "name": "lease_cancellation_request_created",
        "label": "Lease Cancellation Request Created",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable  or disable notifications for when a tenant creates a lease cancellation request"
    },
    {
        "type": "notifications",
        "hidden": false,
        "name": "lease_renewal_request_created",
        "label": "Lease Renewal Request Created",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable  or disable notifications for when a tenant creates a lease renewal request"
    },
    {
        "type": "notifications",
        "hidden": false,
        "name": "lease_renewal_agreement_signed",
        "label": "Lease Renewal Agreement Signed",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable  or disable notifications for when a tenant signs a lease renewal agreement"
    },
    {
        "type": "notifications",
        "hidden": false,
        "name": "rental_application_created",
        "label": "Rental Application Created",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable  or disable notifications for when a tenant creates a rental application"
    },
    {
        "type": "notifications",
        "hidden": false,
        "name": "invoice_paid",
        "label": "Invoice Paid",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable  or disable notifications for when a tenant pays an invoice"
    },
    {
        "type": "notifications",
        "hidden": false,
        "name": "new_tenant_registration_complete",
        "label": "New Tenant Registration Complete",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable  or disable notifications for when a new tenant completes registration"
    },
    {
        "type": "notifications",
        "hidden": false,
        "label": "Message Received",
        "name": "message_received",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable or disable notifications for when you receive a message"
    }
]
""" 

default_staff_privileges_json = """
[
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "all_permissions",
    "label": "All Permissions",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions  for all resources"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "rental_assignments",
    "label": "Rental Assignments",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to the rental units, rental properties or portolios that the staff has been assigned to"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "billing_entries",
    "label": "Billing Entries",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to billing entries"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "staff_invites",
    "label": "Staff Invites",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to staff invites"
  },
   {
    "type": "staff_privilege",
    "hidden": false,
    "name": "lease_agreements",
    "label": "Lease Agreements",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to lease agreements"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "lease_renewal",
    "label": "Lease Renewals",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to lease renewals"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "lease_cancellation",
    "label": "Lease Cancellations",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to lease cancellations"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "maintenance_requests",
    "label": "Maintenance Requests",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to maintenance requests"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "rental_applications",
    "label": "Rental Applications",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to rental applications"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "announcements",
    "label": "Announcements",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to announcements"
  },
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "lease_templates",
    "label": "Lease Templates",
    "values": [
      { "name": "add", "value": false, "inputType": "switch", "label": "Create" },
      { "name": "view", "value": false, "inputType": "switch", "label": "View" },
      { "name": "edit", "value": false, "inputType": "switch", "label": "Edit" },
      { "name": "delete", "value": false, "inputType": "switch", "label": "Delete" }
    ],
    "description": "Enable or disable access and specific actions to lease templates"
  }
]

"""
default_staff_assignments_json = """
  {
    "type": "staff_privilege",
    "hidden": false,
    "name": "rental_assignments",
    "label": "Rentals Under Management",
    "assignment_type": "units",
    "value": [],
    "description": "Properties, units, and portfolios staff can access"
  }
"""

default_tenant_preferences_json = """
[
    {
        "type": "notifications",
        "hidden": false,
        "label": "New Bill Due",
        "name": "bill_created",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable or disable notifications for when a bill is created or you are automatically charged"
    },
    {
        "type": "notifications",
        "hidden": false,
        "label": "Lease Cancellation Request Approval",
        "name": "lease_cancellation_request_approved",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable or disable notifications for when a lease cancellation request is approved"
    },
    {
        "type": "notifications",
        "hidden": false,
        "label": "Lease Cancellation Request Denial",
        "name": "lease_cancellation_request_denied",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable or disable notifications for when a lease cancellation request is denied"
    },
    {
        "type": "notifications",
        "hidden": false,
        "label": "Lease Renewal Request Approval",
        "name": "lease_renewal_request_approved",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false,"inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable or disable notifications for when a lease renewal request is approved"
    },
    {
        "type": "notifications",
        "hidden": false,
        "label": "Lease Renewal Request Rejection",
        "name": "lease_renewal_request_rejected",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable or disable notifications for when a lease renewal request is rejected"
    },
    {
        "type": "notifications",
        "hidden": false,
        "label": "Message Received",
        "name": "message_received",
        "values": [
            {"name": "push", "value": false, "inputType":"switch", "label": "Push Notifications"},
            {"name": "email", "value": false, "inputType":"switch", "label": "Email Notifications"}
        ],
        "description": "Enable or disable notifications for when you receive a message"
    }
]
"""

class Owner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None, unique=True, blank=False, null=False)
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    date_joined = models.DateTimeField(default=datetime.now, blank=True)
    preferences = models.TextField(blank=True, null=True, default=default_owner_preferences_json) #JSON string of default owner preferences

    class Meta:
        db_table = "owners"

    def __str__(self):
        return f"Owner {self.user}"


class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None, unique=True, blank=False, null=False)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, default=None, related_name="owner_staff")
    role = models.CharField(max_length=255, blank=True, null=True) #Custom id for the employee set by owner. Possible values: "property manager", "employee", "maintenance", "other"
    privileges = models.TextField(blank=True, null=True, default=default_staff_privileges_json) #JSON String to Tell the account what they can do to each resource type (rental unit, tenant, etc.). Possible values: "create","read", "update", "delete", "all"
    rental_assignments = models.TextField(blank=True, null=True, default=default_staff_assignments_json) #JSON String to Tell the account what they can do to each resource type (rental unit, tenant, etc.). Possible values: "create","read", "update", "delete", "all"
    date_joined = models.DateTimeField(default=datetime.now, blank=True)
    active_until = models.DateTimeField(blank=True, null=True)#Date the account is active until

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
    preferences = models.TextField(blank=True, null=True, default=default_tenant_preferences_json) #JSON string of default tenant preferences

    class Meta:
        db_table = "tenants"

    def __str__(self):
        return f"Tenant {self.user.first_name} {self.user.last_name}"
    

class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None, unique=True, blank=True, null=True)
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    date_joined = models.DateTimeField(default=datetime.now, blank=True)

    class Meta:
        db_table = "vendors"

    def __str__(self):
        return f"Vendor {self.user}"
