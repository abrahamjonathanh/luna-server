from django.conf import settings
from django.db import models
import uuid
from datetime import timedelta
from django.utils import timezone

def get_default_token_expiry():
    return timezone.now() + timedelta(days=1)

class AuthToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='auth_tokens',
        on_delete=models.CASCADE
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_default_token_expiry)

    def is_valid(self):
        return self.expires_at > timezone.now()

    @classmethod
    def get_or_create_token(cls, user):
        token_instance, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'token': uuid.uuid4().hex,
                'expires_at': timezone.now() + timedelta(days=1)
            }
        )
        if not created:
            token_instance.expires_at = timezone.now() + timedelta(days=1)
            token_instance.save()
        return token_instance

    def __str__(self):
        return f"Token for {self.user.username}: {self.token}"