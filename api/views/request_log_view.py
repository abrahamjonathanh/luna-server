from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.exceptions import ValidationError
from django.db import connection

from template.serializers.request_log_serializer import RequestLogSerializer
from api.models.application_model import Application

import pandas as pd
import time

class RequestLogView(ViewSet):
    # Add pagination to the request log view.

    @staticmethod
    def get_all_requestlogs():
        applications = Application.objects.all()

        query_cols = "id, user, path, body, method, ip_address, user_agent, city, country_name, process_time_ms, status_code, error_message, created_at"
        queries = []
        
        for schema in applications:
            app_name = schema.app.lower()
            queries.append(f"SELECT {query_cols}, '{app_name}' as app_name FROM {app_name}.template_requestlog")
        
        query = " UNION ".join(queries) + " ORDER BY created_at"
        df = pd.read_sql_query(query, connection)

        return df

    def list(self, request):
        """
        Return a list of all request logs.
        """
        request_logs = self.get_all_requestlogs()

        success_requests = request_logs[request_logs['status_code'] < 400]
        client_error_requests = request_logs[(request_logs['status_code'] >= 400) & (request_logs['status_code'] < 500)]
        server_error_requests = request_logs[request_logs['status_code'] >= 500]

        # Get 7 days date range before the current date to get the complete date range.
        complete_date_range = pd.date_range(end=pd.Timestamp.now().date(), periods=7, freq='D')

        request_chart = request_logs.groupby(request_logs['created_at'].dt.date).size().reindex(complete_date_range).fillna(0)
        response_time_chart = request_logs.groupby(request_logs['created_at'].dt.date)['process_time_ms'].mean().round(2).reindex(complete_date_range).fillna(0)
        
        # Application chart
        app_categories = request_logs['app_name'].unique()
        app_success_series = request_logs[request_logs['status_code'] < 400].groupby('app_name').size()
        app_error_series = request_logs[request_logs['status_code'] >= 400].groupby('app_name').size()
        app_chart_series = [
            {
                'name': 'Success',
                'data': app_success_series.reindex(app_categories).fillna(0).tolist()
            },
            {
                'name': 'Error',
                'data': app_error_series.reindex(app_categories).fillna(0).tolist()
            }
        ]

        # Status code chart
        status_code_categories = sorted(request_logs['status_code'].unique())
        status_code_series = [
            {
            'name': app_name,
            'data': request_logs[request_logs['app_name'] == app_name].groupby('status_code').size().reindex(status_code_categories).fillna(0).tolist()
            }
            for app_name in app_categories
        ]

        # Top 10 slowest requests.
        top_10_slowest_requests = request_logs.groupby('path')['process_time_ms'].mean().sort_values(ascending=False).head(10)
        top_10_slowest_requests = request_logs[request_logs['path'].isin(top_10_slowest_requests.index)].groupby('path').agg({
            'method': lambda x: x.unique().tolist(),
            'process_time_ms': lambda x: round(x.mean(), 3)
        }).sort_values(by='process_time_ms', ascending=False).reset_index()

        # Recently errors
        recently_errors = request_logs[request_logs['status_code'] >= 400][['id', 'path', 'method', 'status_code', 'error_message', 'created_at', 'app_name']].sort_values(by='created_at', ascending=False).head(10)

        df = request_logs.sort_values(by='created_at', ascending=False).to_dict(orient='records')
        # time.sleep(3)
        return Response({
            'general': {
                'total_requests': len(df),
                'success_requests': len(success_requests),
                'client_error_requests': len(client_error_requests),
                'server_error_requests': len(server_error_requests),
                'success_rate': f"{round(len(success_requests) / len(df) * 100, 2)}%",
                'client_error_rate': f"{round(len(client_error_requests) / len(df) * 100, 2)}%",
                'server_error_rate': f"{round(len(server_error_requests) / len(df) * 100, 2)}%",
                'average_response_time': round(request_logs['process_time_ms'].mean(), 2)
            },
            'request_chart': {
                # Change categories format to get date only.
                'categories': request_chart.index.strftime('%Y-%m-%d').tolist(),
                'series': [
                    {
                        'name': 'Requests',
                        'data': request_chart.values
                    }
                ]
            },
            'response_time_chart': {
                'series': [
                    {
                        'name': 'Response Time (ms)',
                        'data': response_time_chart.values
                    }
                ]
            },
            'app_chart': {
                'categories': app_categories.tolist(),
                'series': app_chart_series
            },
            'status_code_chart': {
                'categories': status_code_categories,
                'series': status_code_series
            },
            'top_10_slowest_requests': top_10_slowest_requests.to_dict(orient='records'),
            'recently_errors': recently_errors.to_dict(orient='records'),
            'data': df
        }, status=HTTP_200_OK)

    def create(self, request):
        """
        Create a new request log.
        """
        serializer = RequestLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        else:
            raise ValidationError(serializer.errors)

    def retrieve(self, request, pk=None):
        """
        Return a specific request log.
        """
        applications = Application.objects.all()

        query_cols = "id, user, path, body, method, ip_address, user_agent, " \
        "city, country_name, process_time_ms, status_code, error_message, created_at"
        queries = []
        
        for schema in applications:
            app_name = schema.app.lower()
            queries.append(f"SELECT {query_cols}, '{app_name}' as app_name FROM {app_name}.template_requestlog")
        
        query = " UNION ".join(queries) + " ORDER BY created_at"
        df = pd.read_sql_query(query, connection)
        data = df.to_dict(orient='records')
        
        return Response({
            'message': 'OK', 
            'data': data
            }, status=HTTP_200_OK)
