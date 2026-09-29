from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Số điện thoại")
    id_card = models.CharField(max_length=12, unique=True, null=True, blank=True, verbose_name="Số CCCD")
    role = models.CharField(max_length=20, default='user', verbose_name="Vai trò")

    def __str__(self):
        return f"{self.user.username} - CCCD: {self.id_card}"
