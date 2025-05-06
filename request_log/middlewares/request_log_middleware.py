from django.contrib.gis.geoip2 import GeoIP2
from request_log.models.request_log_model import RequestLog
from template.utils.threading import set_current_request_log

import time
import json

class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        whitelisted_urls = [
            "/favicon.ico",
            # "/api/request-log/"
        ]
        
        for url in whitelisted_urls:
            if url in request.path:
                return self.get_response(request)
            
        start_time = time.time()

        client_ip = self.get_client_ip_address(request)
        print(f"Client IP: {client_ip}")
        g = GeoIP2()

        try:
            location_data = g.city(client_ip)  # Get city info based on IP
        except Exception:
            location_data = {"city": None, 'country_name': None}

        data = {
            'user': 'Anonymous',
            'path': request.path,
            'body': {},
            'method': request.method,
            'ip_address': client_ip,
            'user_agent': request.META['HTTP_USER_AGENT'],
            'city': location_data['city'] or None,
            'country_name': location_data['country_name'] or None,
            'process_time_ms': '0',
            'status_code': '0',
            'error_message': None
        }

        # Retrieve request body safely
        try:
            if request.content_type == "application/json":
                body = json.loads(request.body.decode("utf-8"))
            else:
                body = dict(request.POST)
        except json.JSONDecodeError:
            body = {}

        data['body'] = json.dumps(body, default=str)  # Ensure serialization

        req_log = RequestLog(**data)
        set_current_request_log(req_log)  # Store in thread-local storage

        response = self.get_response(request)

        # Update log with response details
        req_log.process_time_ms = round(time.time() - start_time, 4)  # Convert to ms
        req_log.status_code = response.status_code

        if response.status_code == 400 and req_log.error_message is None:
            req_log.error_message = f'Response: {response.data}'

        req_log.save()

        return response
    
    def get_client_ip_address(self, request):
        req_headers = request.META
        x_forwarded_for_value = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for_value:
            ip_addr = x_forwarded_for_value.split(',')[-1].strip()
        else:
            ip_addr = req_headers.get('REMOTE_ADDR')
        return ip_addr
    