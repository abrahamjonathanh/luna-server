from api.models.application_model import Application
from rest_framework import serializers

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = '__all__'