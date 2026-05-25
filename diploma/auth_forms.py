import os
import urllib.request
import urllib.parse
import json
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.core.exceptions import ValidationError

def verify_turnstile(request):
    """Перевіряє токен Cloudflare Turnstile через API."""
    token = request.POST.get('cf-turnstile-response')
    secret_key = os.getenv('TURNSTILE_SECRET_KEY')
    
    if not secret_key: return True  # Fail-open якщо ключ ще не додано в .env
    if not token: return False
        
    url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    data = urllib.parse.urlencode({
        'secret': secret_key,
        'response': token,
        'remoteip': request.META.get('HTTP_CF_CONNECTING_IP', request.META.get('REMOTE_ADDR'))
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode())
            return result.get('success', False)
    except Exception:
        return True # Fail-open якщо сам сервіс Cloudflare недоступний

class TurnstileAuthenticationForm(AuthenticationForm):
    def clean(self):
        if self.request and self.request.method == 'POST':
            if not verify_turnstile(self.request):
                raise ValidationError("Перевірка безпеки (Turnstile) не пройдена. Спробуйте ще раз.")
        return super().clean()

class TurnstilePasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        # Витягуємо request з аргументів, щоб він не потрапив у батьківський клас
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        # Для PasswordResetForm request доведеться прокинути через view
        if hasattr(self, 'request') and self.request and self.request.method == 'POST':
            if not verify_turnstile(self.request):
                raise ValidationError("Перевірка безпеки (Turnstile) не пройдена. Спробуйте ще раз.")
        return super().clean()