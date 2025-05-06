# serializers.py
from rest_framework import serializers

class DatabaseTestSerializer(serializers.Serializer):
    database_type = serializers.ChoiceField(choices=["postgresql", "mysql"])
    host = serializers.CharField()
    port = serializers.IntegerField()
    username = serializers.CharField()
    password = serializers.CharField()
    database_name = serializers.CharField()
    schema = serializers.CharField(required=False, allow_blank=True)