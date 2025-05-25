from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.exceptions import APIException

from api.models.configuration_model import Configuration
from api.serializers.configuration_serializer import ConfigurationSerializer
from template.redis_client import redis_instance
import ast
from template.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django_celery_beat.models import PeriodicTask, IntervalSchedule


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
                        'RECIPIENTS'
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
                
            if 'RECIPIENTS' in redis_data:
                recipients_raw = redis_data['RECIPIENTS']
                if isinstance(recipients_raw, bytes):  # Redis returns bytes
                    recipients_raw = recipients_raw.decode()

                try:
                    # Safely parse the stringified list
                    recipients_list = ast.literal_eval(recipients_raw)
                    if isinstance(recipients_list, list):
                        redis_data['RECIPIENTS'] = recipients_list
                    else:
                        redis_data['RECIPIENTS'] = []
                except (ValueError, SyntaxError):
                    redis_data['RECIPIENTS'] = []
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
