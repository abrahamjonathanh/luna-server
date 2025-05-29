from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from template.redis_client import redis_instance
from template.authentication import TokenAuthentication

from api.models.configuration_model import Configuration
from api.models.application_model import Application
from api.serializers.configuration_serializer import ConfigurationSerializer
from django_celery_beat.models import PeriodicTask, IntervalSchedule

import ast

class ConfigurationView(ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List all configurations from Redis cache."""
        REQUIRED_KEYS = ['DEFAULT_DATE_RANGE',
                        'ALERT_ACTIVATED',
                        'ERROR_RATE_THRESHOLD',
                        'RESPONSE_TIME_THRESHOLD',
                        'SEND_EMAIL_EVERY',
                        'RECIPIENTS',
                        'APPLICATIONS'
                        ]
        
        try:
            # Check if Redis is running properly
            redis_instance.ping()
            redis_data = redis_instance.keys('*')
            if all(key in redis_data for key in REQUIRED_KEYS):
                # If Redis connection is successful and data is not empty
                redis_data = { key : redis_instance.get(key) for key in redis_data}
                print("Redis connection successful.")
            else:
                config_values = Configuration.objects.filter().values('pk', 'value')
                if config_values:
                    redis_data = {item['pk']: item['value'] for item in config_values}
                    # Set the data into Redis
                    for key, value in redis_data.items():
                        print(f"Setting {key} in Redis with value {value}")
                        redis_instance.set(key, value)
                else:
                    raise APIException("No data found in PostgreSQL.")
                
            for key in ['RECIPIENTS', 'APPLICATIONS']:
                if key in redis_data:
                    raw_value = redis_data[key]
                    if isinstance(raw_value, bytes):  # Redis returns bytes
                        raw_value = raw_value.decode()

                    try:
                        # Safely parse the stringified list
                        parsed_list = ast.literal_eval(raw_value)
                        if isinstance(parsed_list, list):
                            redis_data[key] = parsed_list
                        else:
                            redis_data[key] = []
                    except (ValueError, SyntaxError):
                        redis_data[key] = []
        except Exception:
            print("Redis connection failed. Fetching data from PostgreSQL.")
            # If Redis connection fails, fetch data from PostgreSQL
            config_values = Configuration.objects.filter().values('pk', 'value')
            if config_values:
                redis_data = {item['pk']: item['value'] for item in config_values}
            else:
                raise APIException("No data found in PostgreSQL either.")
        
        return Response(redis_data)

    def create(self, request):
        """Create or update configurations based on the request body and store them in Redis for caching."""

        # Store data from the body request, where each key-value pair will be stored or updated as a configuration
        data = request.data

        processed_configurations = []
        for name, value in data.items():
            # Check if the name already exists in the database
            configuration, _ = Configuration.objects.update_or_create(
                key=name.upper(),  # Convert the 'key' to uppercase for lookup
                defaults={"value": value}
            )
            
            if name.upper() == 'SEND_EMAIL_EVERY':
                # Create or update the periodic task for sending emails
                schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=int(value),
                    period=IntervalSchedule.MINUTES,
                )
                
                PeriodicTask.objects.update_or_create(
                    name='Check API Errors Interval',
                    defaults={
                        'interval': schedule,
                        'task': 'api.tasks.check_error_rates_and_alert',
                        'enabled': True,
                        'args': '[]',
                        'kwargs': '{}',
                    },
                )

            if name.upper() == "APPLICATIONS":
                # Convert the value to a list if it's a string representation of a list
                if isinstance(value, str):
                    try:
                        value = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        value = []

                # Remove applications from the database that are not in the new value list
                existing_apps = set(Application.objects.values_list('app', flat=True))
                new_apps = set(value)
                apps_to_remove = existing_apps - new_apps
                if apps_to_remove:
                    Application.objects.filter(app__in=apps_to_remove).delete()
                # Store each application into the Application model
                for app_data in value:
                    # Assuming app_data is a dict with required fields for Application
                    Application.objects.update_or_create(
                        app=app_data,
                        defaults={
                            "app": app_data
                        }
                    )

            try:
                # Check if Redis is running properly
                redis_instance.ping()
                redis_key = str(configuration.id)  # Ensure Redis key is a string
                redis_value = str(value)  # Ensure Redis value is a string
                redis_instance.set(redis_key, redis_value)
            except Exception as e:
                print(f"Redis connection failed. {e}")
                
            # Store the key-value pair in Redis

            processed_configurations.append(ConfigurationSerializer(configuration).data)

        return Response({"message": "Configurations processed successfully", "data": processed_configurations}, status=201)
