from request_log.models import RequestLog
from rest_framework import serializers

class RequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestLog
        fields = '__all__'