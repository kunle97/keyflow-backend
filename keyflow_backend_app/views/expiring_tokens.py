# views/expiring_token.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from token_extension.models import ExpiringToken
from django.utils import timezone

class TokenValidationView(APIView):
    def post(self, request):
        token_key = request.data.get('token')
        if not token_key:
            return Response({
                'message': 'Token is required.',
                'isValid': False,
                'type': 'token_required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = Token.objects.get(key=token_key)
        except Token.DoesNotExist:
            return Response({
                'message': 'Invalid token.',
                'isValid': False,
                'type': 'token_invalid'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            exp_token = ExpiringToken.objects.get(token=token)
            if exp_token.expiration_date < timezone.now():
                return Response({
                    'message': 'Token has expired.',
                    'isValid': False,
                    'type': 'token_expired'
                }, status=status.HTTP_403_FORBIDDEN)
        except ExpiringToken.DoesNotExist:
            return Response({
                'message': 'Token missing expiration data.',
                'isValid': False,
                'type': 'token_invalid'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not token.user.is_active:
            return Response({
                'message': 'User is not active.',
                'isValid': False,
                'type': 'user_not_active'
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'message': 'Token is valid.',
            'isValid': True,
            'type': 'token_valid'
        }, status=status.HTTP_200_OK)