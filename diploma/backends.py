from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        try:
            # Шукаємо користувача або за логіном (username), або за поштою (email)
            user = UserModel.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except UserModel.DoesNotExist:
            # Для запобігання timing attacks виконуємо перевірку пароля навіть якщо користувача не знайдено
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # Якщо кілька акаунтів мають однаковий email
            user = UserModel.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).order_by('id').first()
            
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None