from turtle import pd
from .test_setup import TestSetUp
from rest_framework import status
import pdb
class TestViews(TestSetUp):

    def test_user_cannot_register_with_no_data(self):
        response = self.client.post(self.register_url)
        pdb.set_trace()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_register(self):
        response = self.client.post(self.register_url, self.user_data, format="json")
        pdb.set_trace()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)