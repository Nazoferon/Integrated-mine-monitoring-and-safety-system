from django import forms
from django.contrib.auth.models import User
from .models import UserProfile
from django.core.exceptions import ValidationError

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Імʼя',
            'last_name': 'Прізвище', 
            'email': 'Email'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Введіть ім’я'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Введіть прізвище'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Введіть email'}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_photo', 'phone_number', 'bio']
        labels = {
            'profile_photo': 'Фото профілю',
            'phone_number': 'Номер телефону',
            'bio': 'Про себе'
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Розкажіть трохи про себе...'}),
            'phone_number': forms.TextInput(attrs={'placeholder': '+380XXXXXXXXX'}),
            'profile_photo': forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/jpg'}),
        }

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:  # 5 МБ
                raise ValidationError('Файл занадто великий. Максимальний розмір: 5 МБ.')
        return photo