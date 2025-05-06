from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from api.models.configuration_model import Configuration
from api.serializers.configuration_serializer import ConfigurationSerializer
from django.core.cache import cache  # Import cache for Redis
from redis.exceptions import ConnectionError as RedisConnectionError

class ConfigurationView(ViewSet):
    def list(self, request):
        """List all configurations from Redis cache."""
        configurations = []
        try:
            keys = cache.keys('*')  # Get all keys from Redis
        except RedisConnectionError as e:
            # Log the error and use the request object for logging context
            print(f"Redis connection error: {e}. User: {request.user if hasattr(request, 'user') else 'Unknown'}")
            keys = []  # Fallback to an empty list if Redis is unavailable

        if not keys:  # Check if Redis is empty
            queryset = Configuration.objects.all()  # Fallback to database if cache is empty
            for configuration in queryset:
                cache.set(configuration.key, configuration.value)

        keys = cache.keys('*')  # Get all keys from Redis

        for key in keys:
            value = cache.get(key)  # Get the value for each key
            configurations.append({"id": key, "value": value})

        return Response(configurations)

    def create(self, request):
        """Create or update configurations based on the request body and store them in Redis for caching."""

        # Store data from the body request, where each key-value pair will be stored or updated as a configuration
        data = request.data

        processed_configurations = []
        print(request.data)
        for name, value in data.items():
            # Check if the name already exists in the database
            configuration, created = Configuration.objects.update_or_create(
                key=name.upper(),  # Convert the 'key' to uppercase for lookup
                defaults={"value": value}
            )
            
            # Store the key-value pair in Redis
            cache.set(configuration.id, value)

            processed_configurations.append(ConfigurationSerializer(configuration).data)

        return Response({"message": "Configurations processed successfully", "data": processed_configurations}, status=201)
