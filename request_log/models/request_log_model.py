from django.db import models

class RequestLog(models.Model):
    user = models.CharField('user', max_length=255, null=True)
    path = models.TextField('path')
    body = models.TextField('body')
    method = models.CharField('method', max_length=8)
    ip_address = models.GenericIPAddressField('ip_address')
    user_agent = models.TextField('user_agent')
    city = models.CharField('city', max_length=255, null=True)
    country_name = models.CharField('country_name', max_length=255, null=True)
    process_time_ms = models.FloatField('process_time_ms')
    status_code = models.IntegerField('status_code')
    error_message = models.TextField('error_message', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
