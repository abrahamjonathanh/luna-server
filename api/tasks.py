from celery import shared_task
import logging
import pandas as pd
from django.core.cache import cache


from template.redis_client import redis_instance

from api.models.configuration_model import Configuration
from api.views.request_log_view import RequestLogView
from template.view.email_view import SendEmailView

logger = logging.getLogger(__name__)

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from template.serializers.email_serializer import EmailSerializer

from luna.settings import EMAIL_HOST_USER

@shared_task(name="api.tasks.check_error_rates_and_alert")
def check_error_rates_and_alert():
    if not cache.get('ALERT_ACTIVATED', False):
        return
    
    logger.info("🔥 This prints every 15 minutes from Celery task.")

    # Get data from redis
    redis_data = redis_instance.keys('*')

    print(f'Redis data: {redis_data}')

    config_values = Configuration.objects.filter(pk__in=['ERROR_RATE_THRESHOLD', 'RESPONSE_TIME_THRESHOLD']).values('pk', 'value')
    config_dict = {config['pk']: config['value'] for config in config_values}
    
    ERROR_THRESHOLD = float(config_dict.get('ERROR_RATE_THRESHOLD')) if config_dict else 5 # in percent
    RESPONSE_TIME_THRESHOLD = float(config_dict.get('RESPONSE_TIME_THRESHOLD')) if config_dict else 10000 # in milliseconds

    end_date = pd.Timestamp.now(tz='Asia/Jakarta') # Current time in Jakarta timezone
    start_date = end_date - pd.Timedelta(minutes=15) # 15 minutes ago
        
    request_logs = RequestLogView.get_all_requestlogs(start_date=start_date, end_date=end_date)
    print(f'Error Threshold: {ERROR_THRESHOLD}')
    print(f'Response Time Threshold: {RESPONSE_TIME_THRESHOLD}')
    if not request_logs.empty:
        # success_requests = request_logs[request_logs['status_code'] < 400]
        client_error_requests = request_logs[(request_logs['status_code'] >= 400) & (request_logs['status_code'] < 500)]
        server_error_requests = request_logs[request_logs['status_code'] >= 500]
        
        # Percentage of client and server errors
        client_error_percentage = (len(client_error_requests) / len(request_logs)) * 100 if len(request_logs) > 0 else 0
        server_error_percentage = (len(server_error_requests) / len(request_logs)) * 100 if len(request_logs) > 0 else 0
        error_percentage = client_error_percentage + server_error_percentage

        logger.info(f"Client Error Percentage: {client_error_percentage:.2f}%")
        logger.info(f"Server Error Percentage: {server_error_percentage:.2f}%")
        logger.info(f"Total Error Percentage: {error_percentage:.2f}%")

        # Get response time avg
        response_time_avg = request_logs['process_time_ms'].mean() # in milliseconds

        if error_percentage > ERROR_THRESHOLD:
            logger.error(f"Error percentage {error_percentage:.2f}% exceeds threshold of {ERROR_THRESHOLD}%. Sending alert email.")
            
        if response_time_avg > RESPONSE_TIME_THRESHOLD:
            logger.error(f"Average response time {response_time_avg:.2f}s exceeds threshold of {RESPONSE_TIME_THRESHOLD}s. Sending alert email.")

        # logger.info(f"Success Requests: {len(success_requests)}")

    # html_message = render_to_string('email_template.html', {
    #     'subject': 'TEST',
    #     'message': 'hai',
    #     'recipient_name': 'User',  # Use first name or default to 'User'
    # })
    # plain_message = strip_tags(html_message)

    # email = EmailMessage(
    #     subject='TEST',
    #     body=html_message,
    #     from_email=EMAIL_HOST_USER,
    #     to=['ipcproject10@gmail.com'],
    # )
    # email.content_subtype = "html"  # Set the email content type to HTML
    # email.send()
