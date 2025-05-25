from django.db import models

class Application(models.Model):
    app = models.CharField('app', max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)