from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from datetime import datetime
class User(AbstractUser):
    ACCOUNT_TYPE_CHOICES = (
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES)
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email

class RentalProperty(models.Model):
    name = models.CharField(max_length=100, blank=True)
    street = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(blank=True, null=True)
    country = models.CharField(max_length=100, default='United States')
    units = models.ManyToManyField('RentalUnit', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    class Meta:
        db_table = 'rental_properties'

    def __str__(self):
        return f"Property {self.name} at {self.street} {self.city}, {self.state} {self.zip_code}"

class RentalUnit(models.Model):
    name = models.CharField(max_length=100, blank=True)
    beds = models.PositiveIntegerField()
    baths = models.PositiveIntegerField()
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #Owner of the unit
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_unit', blank=True, null=True) #Tenant of the unit
    lease_term = models.ForeignKey('LeaseTerm', on_delete=models.CASCADE, blank=True, null=True, default=None)
    is_occupied = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'rental_units'

    def __str__(self):
        return f"Unit {self.name} at {self.rental_property.address}"
    
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
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'lease_agreements'

    def __str__(self):
        return f"Lease Agreement for RentalUnit {self.rental_unit} "

class LeaseTerm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #Landlord that created the lease term
    rent = models.DecimalField(max_digits=10, decimal_places=2)
    term = models.IntegerField() #Integer for duration of lease in months
    description = models.TextField() #descriptionn of the property and lease terms (to be displayed on REntal App page)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    gas_included = models.BooleanField(default=False)
    water_included = models.BooleanField(default=False)
    electric_included = models.BooleanField(default=False)
    repairs_included = models.BooleanField(default=False)
    lease_cancellation_notice_period = models.IntegerField() #Integer for notice period in days
    lease_cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'lease_terms'

    def __str__(self):
        return f"Lease Term for {self.term} months"
    
class MaintenanceRequest(models.Model):
    SERVICE_TYPE_CHOICES = (
        ('plumbing', 'Plumbling'),
        ('electrical', 'Electrical'),
        ('appliance', 'Appliance'),
        ('structural', 'Structural'),
        ('other', 'Other'),
    )
        
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    type = models.CharField(max_length=35, choices=SERVICE_TYPE_CHOICES)
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #related landlord
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_maintenance_request') #related tenant that created the request
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)
    
    class Meta:
        db_table = 'maintenance_requests'

    def __str__(self):
        return f"Maintenance Request for Unit {self.rental_unit.name} at {self.rental_unit.rental_property.address}"
    
class LeaseCancellationRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #tenant that created the lease cancellation request
    unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    lease_agreement = models.ForeignKey(LeaseAgreement, on_delete=models.CASCADE, default=None)
    request_date = models.DateTimeField()
    is_approved = models.BooleanField(default=False)
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'lease_cancellation_requests'

    def __str__(self):
        return f"Cancellation Request for {self.tenant} on Unit {self.unit}"



class RentalApplication(models.Model):
    # Existing fields
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=False) 
    date_of_birth = models.DateField(default=None, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    desired_move_in_date = models.DateField()
    is_archived = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approval_hash = models.CharField(max_length=100, blank=True, null=True, default=None, unique=True)
    unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE, default=None) #Unit that the application is for
    other_occupants = models.BooleanField(default=None)
    pets = models.BooleanField(default=None)
    vehicles = models.BooleanField(default=None)
    convicted = models.BooleanField(default=None)
    bankrupcy_filed = models.BooleanField(default=None)
    evicted = models.BooleanField(default=None)
    employment_history = models.TextField(blank=True, null=True)
    residential_history = models.TextField(blank=True, null=True)
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_application_landlord') #related landlord that created the application
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, blank=True, null=True, related_name='tenant_application_tenant') #related tenant that created the application
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    # New fields
    # paystubs = models.FileField(upload_to='tenant_paystubs/', blank=True, null=True)
    # bank_statements = models.FileField(upload_to='tenant_bank_statements/', blank=True, null=True)
    # references = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'rental_applications'

    def __str__(self):
        return f"{self.first_name} {self.last_name} Rental Application"



#Create a model for transactions that will be used to create a transaction history for each user
class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('expense', 'Expense'),
        ('revenue', 'Revenue'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #landlord related to the transaction
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    description = models.TextField()
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None)
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE,default=None)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_transaction') #related tenant
    payment_intent_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    payment_method_id = models.CharField(max_length=100, blank=True, null=True, default=None)
    created_at = models.DateTimeField(default=datetime.now,  blank=True)
    updated_at = models.DateTimeField(default=datetime.now,  blank=True)

    class Meta:
        db_table = 'transactions'

    def __str__(self):
        return f"Transaction for {self.user} on {self.date}"
