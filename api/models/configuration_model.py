from django.db import models

class Configuration(models.Model):
    id = models.CharField(primary_key=True, max_length=255, editable=False)
    key = models.CharField('key', max_length=255, unique=True)
    value = models.CharField('value', max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.key:
            self.id = self.key.upper()
        super().save(*args, **kwargs)

    # bulk_create id to uppercase
    def bulk_create(self, objs, *args, **kwargs):
        print(objs)
        for obj in objs:
            if obj.key:
                obj.id = obj.key.upper()
        super().bulk_create(objs, *args, **kwargs)
