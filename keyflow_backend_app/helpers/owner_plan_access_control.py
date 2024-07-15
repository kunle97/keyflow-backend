from calendar import c
import os
import stripe
from keyflow_backend_app.models.rental_unit import RentalUnit
from keyflow_backend_app.models.rental_property import RentalProperty
from keyflow_backend_app.models.lease_template import LeaseTemplate
from keyflow_backend_app.models.lease_agreement import LeaseAgreement
from keyflow_backend_app.models.uploaded_file import UploadedFile
from keyflow_backend_app.models.account_type import Owner
unlimited = 99999
unlimited_file_size = 99999999999

class OwnerPlanAccessControl:
    stripe_plan_permission_data = [
        {
            "name": "Keyflow Owner Free Plan",
            "stripe_product_id": None,
            "max_rental_properties": 1,
            "max_rental_units": 4,
            "min_rental_units": 0,
            "max_lease_templates": 1,
            "max_lease_agreements": 50,
            "max_tenants": unlimited,
            "max_file_uploads": 25, #Should be 25
            "max_total_files_size": 5242880,  # 5 MB in bytes
            "announcements_enabled": False,
            "maintenance_requests_enabled": True,
            "rental_applications_enabled": False,
            "portfolios_enabled": False,
            "messaging_enabled": True,
        },
        {
            "name": "Keyflow Owner Standard Plan",
            "stripe_product_id": os.getenv("STRIPE_OWNER_STANDARD_PLAN_PRODUCT_ID"),
            "max_rental_properties": 5,
            "max_rental_units": 15,
            "min_rental_units": 0,
            "max_lease_templates": 2,
            "max_lease_agreements": 150,
            "maxx_tenants": unlimited, 
            "max_file_uploads": 75,
            "max_total_files_size": 157286400,  # 15 MB in bytes
            "announcements_enabled": True,
            "maintenance_requests_enabled": True,
            "rental_applications_enabled": True,
            "portfolios_enabled": False,
            "messaging_enabled": True,
        },
        {
            "name": "Keyflow Owner Professional Plan",
            "stripe_product_id": os.getenv("STRIPE_OWNER_PROFESSIONAL_PLAN_PRODUCT_ID"),
            "max_rental_properties": 50,
            "max_rental_units": 50,
            "min_rental_units": 15,
            "max_lease_templates": 10,
            "max_lease_agreements": 500,
            "max_tenants": unlimited,
            "max_file_uploads": unlimited,
            "max_total_files_size": 1048576000,  # 1 GB in bytes
            "announcements_enabled": True,
            "maintenance_requests_enabled": True,
            "rental_applications_enabled": True,
            "portfolios_enabled": True,
            "messaging_enabled": True,
        },
        {
            "name": "Keyflow Owner Enterprise Plan",
            "stripe_product_id": os.getenv("STRIPE_OWNER_ENTERPRISE_PLAN_PRODUCT_ID"),
            "max_rental_properties": unlimited,
            "max_rental_units": unlimited,
            "min_rental_units": 15,
            "max_lease_templates": unlimited,
            "max_lease_agreements": unlimited,
            "max_tenants": unlimited,
            "max_file_uploads": unlimited,
            "max_total_files_size": unlimited_file_size,  # approximately 10 GB
            "announcements_enabled": True,
            "maintenance_requests_enabled": True,
            "rental_applications_enabled": True,
            "portfolios_enabled": True,
            "messaging_enabled": True,
        },
    ]

    def __init__(self, owner):
        self.owner = owner
        self.plan_data = self.get_owner_plan_permission_data()

    def get_owner_plan_permission_data(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_API_KEY")
        if self.owner.stripe_subscription_id is None:
            return self.stripe_plan_permission_data[0]
        
        subscription = stripe.Subscription.retrieve(self.owner.stripe_subscription_id)
        stripe_product_id = subscription["items"]["data"][0]["plan"]["product"]
        print(stripe_product_id)

        for plan_data in self.stripe_plan_permission_data:
            if plan_data["stripe_product_id"] == stripe_product_id:
                return plan_data

        return self.stripe_plan_permission_data[0]  # Return the free plan data if the stripe product id is not found

    #Create a method called can_create_new_rental_property
    def can_create_new_rental_property(self):
        owner_rental_properties = RentalProperty.objects.filter(owner=self.owner)
        current_property_count = len(owner_rental_properties)
        if current_property_count >= self.plan_data["max_rental_properties"]:
            return False
        return True
    
    #Create  a method called can_create_new_rental_unit
    def can_create_new_rental_unit(self, units_to_add=0):
        owner_rental_units = RentalUnit.objects.filter(owner=self.owner)
        current_unit_count = len(owner_rental_units)
        if current_unit_count >= self.plan_data["max_rental_units"] or current_unit_count + units_to_add > self.plan_data["max_rental_units"]:
            return False
        return True

    #Create  a method called can_create_new_lease_template
    def can_create_new_lease_template(self):
        owner_lease_templates = LeaseTemplate.objects.filter(owner=self.owner)
        if len(owner_lease_templates) >= self.plan_data["max_lease_templates"]:
            return False
        return True
    
    #Create  a method called can_create_new_lease_agreement
    def can_create_new_lease_agreement(self):
        owner_lease_agreements = LeaseAgreement.objects.filter(owner=self.owner)
        if len(owner_lease_agreements) >= self.plan_data["max_lease_agreements"]:
            return False
        return True
    
    #Create a method called can_upload_new_file. Should take file size (in bytes) as an argument
    def can_upload_new_file(self, file_size):
        owner_uploaded_files = UploadedFile.objects.filter(owner=self.owner)
        if len(owner_uploaded_files) >= self.plan_data["max_file_uploads"]:
            return False
        total_files_size = sum([file.file.size for file in owner_uploaded_files])
        if total_files_size + file_size >= self.plan_data["max_total_files_size"]:
            return False
        return True
    
    #Create a method to retrieve the maximum file size for file uploads
    def get_max_file_size(self):
        return self.plan_data["max_total_files_size"]
    
    
    #Create methods for features that are enabled/disabled based on the owner's plan
    def can_use_announcements(self):
        return self.plan_data["announcements_enabled"]
    
    def can_use_maintenance_requests(self):
        return self.plan_data["maintenance_requests_enabled"]
    
    def can_use_rental_applications(self):
        return self.plan_data["rental_applications_enabled"]
    
    def can_use_portfolios(self):
        return self.plan_data["portfolios_enabled"]
    
    def can_use_messaging(self):
        return self.plan_data["messaging_enabled"]
    
    
    

#   Usage:
#   owner = some_owner_instance
#   joes_permissions = OwnerPlanAccessControl(owner)

#   if joes_permissions.can_create_new_rental_unit():
#     RentalUnit.objects.create(...)