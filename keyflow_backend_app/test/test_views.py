from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from keyflow_backend_app.models import RentalProperty, User
from keyflow_backend_app.views import PropertyViewSet
