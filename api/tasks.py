import logging
import pandas as pd
from celery import shared_task
from rest_framework.exceptions import APIException
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from api.models.configuration_model import Configuration
from api.views.request_log_view import RequestLogView
from template.redis_client import redis_instance

from luna.settings import EMAIL_HOST_USER

logger = logging.getLogger(__name__)

@shared_task(name="api.tasks.check_error_rates_and_alert")
def check_error_rates_and_alert():
    """
    Check error rates and send alert emails if necessary.
    This function checks the error rates from Redis and PostgreSQL, and sends an email alert if the error rate exceeds a certain threshold.
    """
    if redis_instance.get('ALERT_ACTIVATED') == 'False':
        return
    
    logger.info("Running Celery task to check error rates and send alert emails.")

    try:
        # Check if Redis is running properly
        redis_instance.ping()
        redis_data = redis_instance.keys('*')

        REQUIRED_KEYS = ['DEFAULT_DATE_RANGE',
                        'ALERT_ACTIVATED',
                        'ERROR_RATE_THRESHOLD',
                        'RESPONSE_TIME_THRESHOLD',
                        'SEND_EMAIL_EVERY']      
          
        if all(key in redis_data for key in REQUIRED_KEYS):
            # If Redis connection is successful and data is not empty
            redis_data = { key : redis_instance.get(key) for key in redis_data}
            logger.info("Redis connection successful.")
        else:
            config_values = Configuration.objects.filter(pk__in=REQUIRED_KEYS).values('pk', 'value')
            if config_values:
                redis_data = {item['pk']: item['value'] for item in config_values}
                # Set the data into Redis
                for key, value in redis_data.items():
                    logger.info(f"Setting {key} in Redis with value {value}")
                    redis_instance.set(key, value)
            else:
                raise APIException("No data found in PostgreSQL.")
    except Exception:
        logger.error("Redis connection failed. Fetching data from PostgreSQL.")
        # If Redis connection fails, fetch data from PostgreSQL
        config_values = Configuration.objects.filter(pk__in=REQUIRED_KEYS).values('pk', 'value')
        if config_values:
            redis_data = {item['pk']: item['value'] for item in config_values}
        else:
            raise APIException("No data found in PostgreSQL either.")

    ERROR_THRESHOLD = float(redis_data.get('ERROR_RATE_THRESHOLD')) if redis_data.get('ERROR_RATE_THRESHOLD') else 10
    RESPONSE_TIME_THRESHOLD = float(redis_data.get('RESPONSE_TIME_THRESHOLD')) if redis_data.get('RESPONSE_TIME_THRESHOLD') else 10000
    SEND_EMAIL_EVERY = int(redis_data.get('SEND_EMAIL_EVERY')) if redis_data.get('SEND_EMAIL_EVERY') else 15
    
    logger.info(f'🔥 This prints every {SEND_EMAIL_EVERY} minutes from Celery task.')

    # Calculate the start and end date for the email
    end_date = pd.Timestamp.now(tz='Asia/Jakarta')
    start_date = end_date - pd.Timedelta(minutes=SEND_EMAIL_EVERY)

    request_logs = RequestLogView.get_all_requestlogs(start_date=start_date, end_date=end_date)

    if not request_logs.empty:
        total_requests = request_logs.shape[0]
        client_error_requests = request_logs[(request_logs['status_code'] >= 400) & (request_logs['status_code'] < 500)].shape[0]
        server_error_requests = request_logs[request_logs['status_code'] >= 500].shape[0]
        
        # Percentage of client and server errors
        client_error_percentage = ((client_error_requests / total_requests) * 100) if total_requests > 0 else 0
        server_error_percentage = ((server_error_requests / total_requests) * 100) if total_requests > 0 else 0
        error_percentage = client_error_percentage + server_error_percentage

        # Check if the error rate or average response time exceeds the threshold exceeds the threshold
        if (error_percentage < ERROR_THRESHOLD) or (request_logs['process_time_ms'].mean() < RESPONSE_TIME_THRESHOLD):
            return

        # Group by URL and service name
        url_error_table = request_logs.groupby(['path', 'app_name']).agg(
            errors_4xx=('status_code', lambda x: ((x >= 400) & (x < 500)).sum() if not x.empty else 0),
            errors_5xx=('status_code', lambda x: (x >= 500).sum() if not x.empty else 0)
        ).reset_index()

        # Filter out rows where both errors_4xx and errors_5xx are zero
        url_error_table = url_error_table[(url_error_table['errors_4xx'] > 0) | (url_error_table['errors_5xx'] > 0)]
        
        url_error_table = url_error_table.rename(columns={
            'path': 'url', 
            'app_name': 'service_name',
        })
        url_error_table = url_error_table.to_dict(orient='records')

        email_data = {
            "start_time": start_date.strftime("%B %d, %Y %H:%M:%S %Z"),
            "end_time": end_date.strftime("%B %d, %Y %H:%M:%S %Z"),
            "total_requests": total_requests,
            "total_4xx": client_error_requests,
            "total_5xx": server_error_requests,
            "error_rate_percent": round(error_percentage, 2),
            "threshold_rate_percent": ERROR_THRESHOLD,
            "response_time": round(request_logs['process_time_ms'].mean(), 2),
            "response_time_threshold": RESPONSE_TIME_THRESHOLD,
            "url_error_table": url_error_table,
        }

        # Send email
        html_message = render_to_string('email_template.html', email_data)

        email = EmailMessage(
            subject= f"Warning! Error Occurred in {email_data['start_time']} - {email_data['end_time']}",
            body=html_message,
            from_email=EMAIL_HOST_USER,
            to=['ipcproject10@gmail.com'],
        )
        email.content_subtype = "html"  # Set the email content type to HTML
        email.send()
        logger.info(f"Email sent successfully")
    else:
        logger.warning(f"No request logs found from {start_date} to {end_date}.")