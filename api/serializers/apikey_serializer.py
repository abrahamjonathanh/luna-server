from rest_framework_api_key.models import APIKey
from rest_framework import serializers

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = '__all__'