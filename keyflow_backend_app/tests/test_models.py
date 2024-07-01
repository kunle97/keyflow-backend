from django.test import TestCase
from keyflow_backend_app.models import rental_property

from keyflow_backend_app.models.rental_property import RentalProperty
from keyflow_backend_app.models.account_type import Owner
from keyflow_backend_app.models.user import User


#Create a test class for the RentalProperty model
class RentalPropertyTest(TestCase):
    """ Test module for RentalProperty model """

    def setUp(self):
        #Create a test user
        user = User.objects.create(
            first_name='John',
            last_name='Doe',
            email="johndoe@email.com",
            password="password",
            account_type="owner",
        )
        #Create a test owner
        owner = Owner.objects.create(
            user=user,
        )
        rental_property = RentalProperty.objects.create(
            owner=owner,
            name='Test Rental Property',
            address='Test Address',
            city='Test City',
            state='Test State',
            zip_code='Test Zipcode',
            country='Test Country',
            portfolio='Test Portfolio',
        )

def test_create_rental_property_with_valid_data(self):
        rental_property = RentalProperty.objects.get(id=1, name='Test Rental Property')
  
        self.assertEqual(rental_property.name, 'Test Rental Property')
        self.assertEqual(rental_property.street, 'Test Street')
        self.assertEqual(rental_property.city, 'Test City')
        self.assertEqual(rental_property.state, 'Test State')
        self.assertEqual(rental_property.zip_code, 'Test Zipcode')
        self.assertEqual(rental_property.country, 'Test Country')
        self.assertEqual(rental_property.name, 'Test Rental Property')
        self.assertEqual(rental_property.street, 'Test Street')
        self.assertEqual(rental_property.city, 'Test City')
        self.assertEqual(rental_property.state, 'Test State')
        self.assertEqual(rental_property.zip_code, 'Test Zipcode')
        self.assertEqual(rental_property.country, 'Test Country')