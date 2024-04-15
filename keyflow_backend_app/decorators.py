from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from .models.expiring_token import ExpiringToken

def check_token_expiry(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        token = request.headers.get('Authorization')
        if token:
            try:
                token_obj = ExpiringToken.objects.get(key=token)
                if token_obj.expiration_date < timezone.now():
                    return JsonResponse({'error': 'Token expired'}, status=401)
            except ExpiringToken.DoesNotExist:
                return JsonResponse({'error': 'Invalid token'}, status=401)
        else:
            return JsonResponse({'error': 'Token missing'}, status=401)
        
        return view_func(request, *args, **kwargs)

    return wrapped_view
