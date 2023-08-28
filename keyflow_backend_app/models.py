from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model

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
    
    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email

class RentalProperty(models.Model):
    name = models.CharField(max_length=100, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.PositiveIntegerField(blank=True, null=True)
    country = models.CharField(max_length=100, default='United States')
    units = models.ManyToManyField('RentalUnit', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)

    class Meta:
        db_table = 'rental_properties'

    def __str__(self):
        return f"Property {self.name} at {self.address}"

class RentalUnit(models.Model):
    name = models.CharField(max_length=100, blank=True)
    beds = models.PositiveIntegerField()
    baths = models.PositiveIntegerField()
    rent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #Owner of the unit
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_unit', blank=True, null=True) #Tenant of the unit
    least_term = models.ForeignKey('LeaseTerm', on_delete=models.CASCADE, blank=True, null=True, default=None)

    class Meta:
        db_table = 'rental_units'

    def __str__(self):
        return f"Unit {self.name} at {self.rental_property.address}"
    
class LeaseAgreement(models.Model):
    rental_property = models.ForeignKey('RentalProperty', on_delete=models.CASCADE)
    rental_unit = models.ForeignKey('RentalUnit', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    document_id = models.CharField(max_length=100, blank=True, null=True)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant')
    lease_term = models.ForeignKey('LeaseTerm', on_delete=models.CASCADE, blank=True, null=True, default=None)
    signed_date = models.DateField()
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='landlord') #Landlord that created the lease agreement
    approval_hash = models.CharField(max_length=100, blank=True, null=True)
    class Meta:
        db_table = 'lease_agreements'

    def __str__(self):
        return f"Lease Agreement for RentalUnit {self.rental_unit} at {self.rental_property}"

class LeaseTerm(models.Model):
    rent = models.DecimalField(max_digits=10, decimal_places=2)
    term = models.IntegerField() #Integer for duration of lease in months
    description = models.TextField() #descriptionn of the property and lease terms (to be displayed on REntal App page)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2)
    secutiry_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    gas_included = models.BooleanField(default=False)
    water_included = models.BooleanField(default=False)
    electric_included = models.BooleanField(default=False)
    repairs_included = models.BooleanField(default=False)
    lease_cancellation_notice_period = models.IntegerField() #Integer for notice period in days
    lease_cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'lease_terms'

    def __str__(self):
        return f"Lease Term for {self.term} months"
    
class MaintenanceRequest(models.Model):
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE)
    description = models.TextField()
    resolved = models.BooleanField(default=False)
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, default=None) #related landlord
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_maintenance_request') #related tenant that created the request

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
    is_approved = models.BooleanField(default=False)
    unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE, default=None) #Unit that the application is for
    approval_hash = models.CharField(max_length=100, blank=True, null=True, default=None)
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
    date = models.DateField()
    description = models.TextField()
    rental_property = models.ForeignKey(RentalProperty, on_delete=models.CASCADE,default=None)
    rental_unit = models.ForeignKey(RentalUnit, on_delete=models.CASCADE,default=None)
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, default=None, related_name='tenant_transaction') #related tenant

    class Meta:
        db_table = 'transactions'

    def __str__(self):
        return f"Transaction for {self.user} on {self.date}"
