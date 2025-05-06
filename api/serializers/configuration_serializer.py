from api.models.configuration_model import Configuration
from rest_framework import serializers

class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        fields = '__all__'