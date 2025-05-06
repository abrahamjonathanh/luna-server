from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.db import connection

from request_log.serializers.request_log_serializer import RequestLogSerializer
from api.models.application_model import Application

import pandas as pd

class RequestLogView(ViewSet):
    @staticmethod
    def get_all_requestlogs(start_date=None, end_date=None, application_name=None, status_code=None, request_method=None):
        query_cols = "id, user, path, body, method, ip_address, user_agent, city, country_name, process_time_ms, status_code, error_message, created_at"
        queries = []

        if application_name is None:
            applications = Application.objects.all()
        else:
            applications = Application.objects.filter(app=application_name)
        
        for schema in applications:
            app_name = schema.app.lower()
            queries.append(f"SELECT {query_cols}, '{app_name}' as app_name FROM {app_name}.request_log_requestlog")
        
        query = " UNION ".join(queries)
        
        # Add WHERE clauses based on the provided filters
        where_clauses = []
        
        # Add filters for start_date and end_date
        if start_date and end_date:
            where_clauses.append(f"created_at BETWEEN '{start_date}' AND '{end_date}'")

        # Add filter for status_code
        if status_code:
            where_clauses.append(f"status_code = {status_code}")

        if request_method:
            where_clauses.append(f"method = '{request_method}'")
        
        if where_clauses:
            query = f"SELECT * FROM ({query}) AS combined_query WHERE {' AND '.join(where_clauses)}"
        else:
            query = f"SELECT * FROM ({query}) AS combined_query"

        query += " ORDER BY created_at"

        df = pd.read_sql_query(query, connection)

        # Transform 'created_at' column to datetime with timezone Asia/Jakarta
        if 'created_at' in df.columns and not df['created_at'].empty:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('Asia/Jakarta')

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
            'time_chart': {
                # Change categories format to get date only.
                'categories': request_chart.index.strftime('%Y-%m-%d').tolist(),
                'request_series': [
                    {
                        'name': 'Requests',
                        'data': request_chart.values
                    }
                ],
                'response_time_series': [
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
            'data_table': df
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
        data = self.get_all_requestlogs(status_code=500)
        
        return Response({
            'message': 'OK', 
            'data': data.to_dict(orient='records')
            }, status=HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='overview')
    def get_overview(self, request):
        """
        Return a list of all request logs.
        """
        try:
            start_date = pd.to_datetime(request.data.get('start_date', pd.Timestamp.now(tz='Asia/Jakarta') - pd.Timedelta(days=1))).tz_convert('Asia/Jakarta')
            end_date = pd.to_datetime(request.data.get('end_date', pd.Timestamp.now(tz='Asia/Jakarta'))).tz_convert('Asia/Jakarta')
        except ValueError:
            return Response({'error': 'Invalid start_date format'}, status=HTTP_400_BAD_REQUEST)

        status_code = request.data.get('status_code', None)
        application_name = request.data.get('application_name', None)
        request_method = request.data.get('request_method', None)

        request_logs = self.get_all_requestlogs(start_date=start_date, end_date=end_date, application_name=application_name, status_code=status_code, request_method=request_method)

        success_requests = request_logs[request_logs['status_code'] < 400]
        client_error_requests = request_logs[(request_logs['status_code'] >= 400) & (request_logs['status_code'] < 500)]
        server_error_requests = request_logs[request_logs['status_code'] >= 500]

        start_date = start_date.replace(second=0, microsecond=0)
        end_date = end_date.replace(second=0, microsecond=0)
        
        delta_days = (end_date - start_date).days
        
        freq, complete_date_range = None, None

        if delta_days <= 2:
            delta_hours = (end_date - start_date).total_seconds() / 3600
            
            if delta_hours <= 1:
                freq = 'min'
            elif delta_hours <= 4:
                freq = '5min'
            elif delta_hours <= 12:
                freq = '10min'
            else:
                freq = 'h'
                start_date, end_date = start_date.replace(minute=0), end_date.replace(minute=0)
        elif delta_days <= 60:
            freq = 'D'
            start_date, end_date = start_date.replace(hour=0, minute=0), end_date.replace(hour=0, minute=0)
        elif delta_days <= 180:
            freq = 'W-SUN'
            start_date, end_date = start_date.replace(hour=0, minute=0), end_date.replace(hour=0, minute=0)
        elif delta_days <= (365 * 5):
            freq = 'MS'
            start_date, end_date = start_date.replace(hour=0, minute=0), end_date.replace(hour=0, minute=0)
        else:
            freq = 'YS-JAN'
            start_date, end_date = start_date.replace(hour=0, minute=0), end_date.replace(hour=0, minute=0)
        
        complete_date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
        print(complete_date_range, freq)
        print(request_logs.groupby(pd.Grouper(key='created_at', freq=freq, origin=start_date)).size())

        request_chart = request_logs.groupby(pd.Grouper(key='created_at', freq=freq, origin=start_date)).size().reindex(complete_date_range).fillna(0)
        response_time_chart = request_logs.groupby(pd.Grouper(key='created_at', freq=freq, origin=start_date))['process_time_ms'].mean().round(2).reindex(complete_date_range).fillna(0)
        
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

        # Request method chart
        request_method_categories = sorted(request_logs['method'].unique())
        request_method_series = [
            {
                'name': app_name,
                'data': request_logs[request_logs['app_name'] == app_name].groupby('method').size().reindex(request_method_categories).fillna(0).tolist()
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
        recently_errors = request_logs[request_logs['status_code'] >= 400][['id', 'path', 'method', 'status_code', 'error_message', 'created_at', 'app_name']].sort_values(by='created_at', ascending=False)

        df = request_logs.sort_values(by='created_at', ascending=False).to_dict(orient='records')

        return Response({
            'filters': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
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
            'time_chart': {
                'categories': request_chart.index.tz_convert('Asia/Jakarta').strftime('%Y-%m-%dT%H:%M:%S%z').tolist(),
                'request_series': [
                    {
                        'name': 'Requests',
                        'data': request_chart.values
                    }
                ],
                'response_time_series': [
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
            'request_method_chart': {
                'categories': request_method_categories,
                'series': request_method_series
            },
            'top_10_slowest_requests': top_10_slowest_requests.to_dict(orient='records'),
            'recently_errors': recently_errors.to_dict(orient='records'),
            'data_table': df
        }, status=HTTP_200_OK)
