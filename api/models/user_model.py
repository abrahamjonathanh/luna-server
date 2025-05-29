from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from .role_model import Role

class User(AbstractBaseUser):
    username = models.CharField('username', max_length=255, unique=True)
    email = models.EmailField('email', max_length=255, unique=True)
    fullname = models.CharField('fullname', max_length=255)
    password = models.CharField('password', max_length=255)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='users')
    is_active = models.BooleanField('is_active', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField('last login', null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'username'

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'user'
        verbose_name_plural = 'users'

