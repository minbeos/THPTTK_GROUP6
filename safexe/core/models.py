from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'Chủ phương tiện'),
        ('rescuer', 'Thợ cứu hộ'),
    )
    full_name = models.CharField(max_length=150, verbose_name="Họ và tên")
    phone = models.CharField(max_length=10, unique=True, null=True, blank=True, verbose_name="Số điện thoại")
    cccd = models.CharField(max_length=12, unique=True, null=True, blank=True, verbose_name="Số CCCD")
    email = models.EmailField(unique=True, verbose_name="Địa chỉ email")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name="Vai trò")

    def __str__(self):
        return f"{self.full_name} ({self.phone})"
