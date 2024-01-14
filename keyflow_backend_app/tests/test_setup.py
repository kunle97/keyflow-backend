from rest_framework.test import APITestCase
from django.urls import reverse

class TestSetUp(APITestCase):
    def setUp(self):
        self.register_url = reverse('api/owners/register')
        self.login_url = reverse('api/auth/login/')
        self.logout_url = reverse('api/auth/logout')
        self.user_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'johndoe@gmail.com',
            'password': 'password',
            'account_type': 'owner',
        }
        return super().setUp()
    
    
    def tearDown(self):
        return super().tearDown()