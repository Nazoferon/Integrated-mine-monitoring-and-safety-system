from django.db import models
from django.contrib.auth.models import User
import os, json
from uuid import uuid4

def user_profile_photo_path(instance, filename):
    """Шлях для збереження фото: media/users/user_<id>/profile_photos/<random_name>.<ext>"""
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('users', f'user_{instance.user.id}', 'profile_photos', filename)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(
        upload_to=user_profile_photo_path,
        blank=True,
        null=True,
        verbose_name="Фото профілю"
    )
    phone_number = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Номер телефону"
    )
    bio = models.TextField(
        blank=True, 
        verbose_name="Біографія",
        max_length=500
    )

    def __str__(self):
        return f"Профіль {self.user.username}"

class MineMap(models.Model):
    name = models.CharField(max_length=100, default="Mine Map")
    map_data = models.JSONField(default=dict)  # JSON для зберігання структури карти
    last_edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_mine_maps')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name