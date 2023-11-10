from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['email'] = user.email
        token['account_type'] = user.account_type
        token['is_active'] = user.is_active
        token['stripe_account_id'] = user.stripe_account_id
        token['stripe_customer_id'] = user.stripe_customer_id
        token['is_active'] = user.is_active

        # ...

        return token
    

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework import status
# from rest_framework.response import Response
# from rest_framework.views import APIView


# class CustomTokenObtainPairView(TokenObtainPairView):
#     def post(self, request, *args, **kwargs):
#         email = request.data.get('email')
#         password = request.data.get('password')

#         # Replace 'User' with your user model
#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

#         if not user.check_password(password):
#             return Response({"detail": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)

#         refresh = RefreshToken.for_user(user)
#         response = super().post(request, *args, **kwargs)
#         if response.status_code == 200:
#             response.data['refresh'] = str(refresh)
#         return response

# class CustomTokenRefreshView(TokenRefreshView):
#     pass

# class CustomTokenVerifyView(APIView):
#     def post(self, request, *args, **kwargs):
#         response = super().post(request, *args, **kwargs)
#         if response.status_code == 200:
#             user = User.objects.get(email=request.data.get('email'))  # Replace 'User' with your user model
#             refresh = RefreshToken.for_user(user)
#             response.data['refresh'] = str(refresh)
#         return response
