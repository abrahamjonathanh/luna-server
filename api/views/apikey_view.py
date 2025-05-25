from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework_api_key.models import APIKey
from api.serializers.apikey_serializer import APIKeySerializer
class CreateAPIKeyView(ViewSet):
    authentication_classes = []

    def list(self, request):
        """
        List all API keys.
        """
        api_keys = APIKey.objects.all()
        serializer = APIKeySerializer(api_keys, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        # return Response({"api_keys": [key.key for key in api_keys]}, status=status.HTTP_200_OK)
        
    def post(self, request):
        name = request.data.get("name", "Unnamed Key")
        api_key, key = APIKey.objects.create_key(name=name)
        return Response({"key": key}, status=status.HTTP_201_CREATED)
