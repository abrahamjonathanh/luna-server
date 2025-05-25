from django.db import models

class Role(models.Model):
    id = models.CharField(primary_key=True, max_length=255, editable=False)
    role = models.CharField('role', max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if self.role:
            self.id = self.role.upper()
        super().save(*args, **kwargs)