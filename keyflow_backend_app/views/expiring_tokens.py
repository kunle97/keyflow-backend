from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models.expiring_token import ExpiringToken

class TokenValidationView(APIView):
    def post(self, request):
        token_key = request.data.get('token')
        if not token_key:
            return Response({'message': 'Token is required.','isValid':False,'type':'token_required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = ExpiringToken.objects.get(key=token_key)
            if token.is_expired():
                return Response({'message': 'Token has expired.','isValid':False, 'type':'token_expired'}, status=status.HTTP_403_FORBIDDEN)
            elif not token.user.is_active:
                return Response({'message': 'User is not active.','isValid':False,'type':'user_not_active'}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'message': 'Token is valid.','isValid':True,'type':'token_valid'}, status=status.HTTP_200_OK)
        except ExpiringToken.DoesNotExist:
            return Response({'message': 'Invalid token.','isValid':False,'type':'token_invalid'}, status=status.HTTP_400_BAD_REQUEST)
