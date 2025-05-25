from api.models.user_model import User
from rest_framework import serializers
from request_log.exceptions.api_exception import ValidationException

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'fullname', 'role', 'last_login', 'is_active', 'created_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }