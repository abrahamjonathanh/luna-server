from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.db import connection

from request_log.serializers.request_log_serializer import RequestLogSerializer
from api.models.application_model import Application

import pandas as pd
from rest_framework.pagination import PageNumberPagination
from concurrent.futures import ThreadPoolExecutor
from request_log.exceptions.api_exception import ValidationException
from template.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
import time
class RequestLogView(ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    DEFAULT_DATE_RANGE = 7

    @staticmethod
    def get_all_requestlogs(role="GUEST", start_date=None, end_date=None, application_name=None, status_code=None, request_method=None, path=None):
        """
        Get all request logs from the database.
        """
        # Define columns for ADMIN and non-ADMIN users
        guest_cols = [
            "id", "path", "method", "country_name", "country_code", "process_time_ms",
            "status_code", "error_message", "created_at"
        ]
        admin_cols = guest_cols + [
            "body", "headers", "ip_address", "user_agent", "city"
        ]

        is_admin = role == 'ADMIN'
        query_cols = ", ".join(admin_cols if is_admin else guest_cols)
        queries = []

        if application_name is None:
            applications = Application.objects.all()
        else:
            applications = Application.objects.filter(app__in=application_name if isinstance(application_name, list) else [application_name])
        
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
            if isinstance(status_code, list):
                status_code_list = ', '.join([f"'{code}'" for code in status_code])
                where_clauses.append(f"status_code IN ({status_code_list})")
            else:
                where_clauses.append(f"status_code = '{status_code}'")

        # Add filter for request_method
        if request_method:
            if isinstance(request_method, list):
                request_method_list = ', '.join([f"'{method}'" for method in request_method])
                where_clauses.append(f"method IN ({request_method_list})")
            else:
                where_clauses.append(f"method = '{request_method}'")
        
        # Add filter for path
        if path:
            if isinstance(path, list):
                path_list = ', '.join([f"'{p}'" for p in path])
                where_clauses.append(f"path IN ({path_list})")
            else:
                where_clauses.append(f"path = '{path}'")

        if where_clauses:
            query = f"SELECT * FROM ({query}) AS combined_query WHERE {' AND '.join(where_clauses)}"
        else:
            query = f"SELECT * FROM ({query}) AS combined_query"

        query += " ORDER BY created_at"

        df = pd.read_sql_query(query, connection)

        # Transform 'created_at' column to datetime with timezone Asia/Jakarta
        if 'created_at' in df.columns and not df['created_at'].empty:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('Asia/Jakarta')

        # Transform empty 'country_name' column into 'Unknown'
        if 'country_name' in df.columns and not df['country_name'].empty:
            df['country_name'] = df['country_name'].fillna('Unknown')

        return df

    @staticmethod
    def determine_frequency(delta_days, delta_hours):
        """
        Determines the frequency for resampling and whether to reset hour/minute to 0.

        Returns:
            (str, bool): Tuple of frequency string and a flag indicating whether to reset time to hour=0.
        """
        if delta_days <= 2:
            if delta_hours <= 1:
                return 'min', False
            elif delta_hours <= 4:
                return '5min', False
            elif delta_hours <= 12:
                return '10min', False
            return 'h', False  
        elif delta_days <= 60: # reset hour to 0 for more than 1 day
            return 'D', True
        elif delta_days <= 180:
            return 'W-SUN', True
        elif delta_days <= (365 * 5):
            return 'MS', True
        return 'YS-JAN', True

    def determine_frequency_and_range(self, start, end):
        """
        Determines the frequency for resampling and the complete date range.
        """
        start = start.replace(second=0, microsecond=0)
        end = end.replace(second=0, microsecond=0)

        delta_days = (end - start).days
        delta_hours = (end - start).total_seconds() / 3600

        freq, reset_time = self.determine_frequency(delta_days, delta_hours)
        if reset_time:
            start = start.replace(hour=0, minute=0)
            end = end.replace(hour=23, minute=59)

        return freq, start, end, pd.date_range(start=start, end=end, freq=freq)

    @staticmethod
    def build_time_chart(request_log, complete_date_range, time_index):
        """
        Build time chart with success and error groups.
        """
        # Success: status_code < 400
        success_series = (
            request_log[request_log['status_code'] < 400]
            .groupby(time_index)
            .size()
            .reindex(complete_date_range)
            .fillna(0)
        )
        # Error: status_code >= 400
        error_series = (
            request_log[request_log['status_code'] >= 400]
            .groupby(time_index)
            .size()
            .reindex(complete_date_range)
            .fillna(0)
        )
        response_series = (
            request_log.groupby(time_index)['process_time_ms']
            .mean()
            .reindex(complete_date_range)
            .round(4)
            .fillna(0)
        )

        return {
            'categories': complete_date_range.tz_convert('Asia/Jakarta').strftime('%Y-%m-%dT%H:%M:%S%z').to_list(),
            'request_series': [
                {
                    'name': 'Success',
                    'data': success_series.to_list()
                },
                {
                    'name': 'Error',
                    'data': error_series.to_list()
                }
            ],
            'response_time_series': [
                {
                    'name': 'Response Time (s)',
                    'data': response_series.to_list()
                }
            ]
        }

    @staticmethod
    def build_app_chart(request_log):
        """
        Build application chart.
        """
        app_categories = request_log['app_name'].dropna().unique()
        
        app_success_series = request_log[request_log['status_code'] < 400].groupby('app_name').size().reindex(app_categories).fillna(0)
        app_error_series = request_log[request_log['status_code'] >= 400].groupby('app_name').size().reindex(app_categories).fillna(0)

        return {
            'categories': app_categories.tolist(),
            'series': [
                {
                    'name': 'Success', 
                    'data': app_success_series.to_list()
                },
                {
                    'name': 'Error', 
                    'data': app_error_series.to_list()
                }
            ]
        }

    @staticmethod
    def build_status_code_chart(request_log):
        """
        Build status code chart.
        """
        status_code_categories = sorted(request_log[request_log['status_code'] >= 400]['status_code'].dropna().unique())
        status_code_series = [
            {
                'name': app_name,
                'data': request_log[request_log['app_name'] == app_name].groupby('status_code').size().reindex(status_code_categories).fillna(0).to_list()
            }
            for app_name in request_log['app_name'].dropna().unique()
        ]

        return {
            'categories': status_code_categories,
            'series': status_code_series
        }

    @staticmethod
    def build_request_method_chart(request_log):
        """
        Build request method chart.
        """
        request_method_categories = sorted(request_log['method'].dropna().unique())
        request_method_series = [
            {
                'name': app_name,
                'data': request_log[request_log['app_name'] == app_name].groupby('method').size().reindex(request_method_categories).fillna(0).to_list()
            }
            for app_name in request_log['app_name'].dropna().unique()
        ]

        return {
            'categories': request_method_categories,
            'series': request_method_series
        }

    @staticmethod
    def build_summary_stats(request_logs):
        """
        Build summary statistics for request logs.
        """
        total = len(request_logs)

        def get_success():
            return request_logs[request_logs['status_code'] < 400]

        def get_client_err():
            return request_logs[(request_logs['status_code'] >= 400) & (request_logs['status_code'] < 500)]

        def get_server_err():
            return request_logs[request_logs['status_code'] >= 500]

        def to_percent(part): return f"{round(len(part) / total * 100, 2)}%" if total else "0%"

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_success = executor.submit(get_success)
            future_client_err = executor.submit(get_client_err)
            future_server_err = executor.submit(get_server_err)

            success = future_success.result()
            client_err = future_client_err.result()
            server_err = future_server_err.result()

        return {
            'total_requests': total,
            'success_requests': len(success),
            'client_error_requests': len(client_err),
            'server_error_requests': len(server_err),
            'success_rate': to_percent(success),
            'client_error_rate': to_percent(client_err),
            'server_error_rate': to_percent(server_err),
            'avg_process_time_ms': round(request_logs['process_time_ms'].mean(), 4) if total else 0
        }

    @staticmethod
    def top_50_slowest_routes(request_logs):
        """
        Get the top 50 slowest routes based on average process time, grouped by app_name and path.
        """
        # Group by app_name and path, calculate mean process_time_ms, and get top 50
        top_50 = (
            request_logs
            .groupby(['app_name', 'path'], as_index=False)['process_time_ms']
            .mean()
            .sort_values(by='process_time_ms', ascending=False)
            .head(50)
        )

        # For each (app_name, path), get unique methods used
        methods = (
            request_logs
            .groupby(['app_name', 'path'])['method']
            .unique()
            .reset_index()
        )

        # Merge methods into top_50
        top_50 = top_50.merge(methods, on=['app_name', 'path'], how='left')

        # Round process_time_ms
        top_50['process_time_ms'] = top_50['process_time_ms'].round(4)

        # Rename columns for clarity
        top_50.rename(columns={'method': 'methods', 'process_time_ms': 'avg_process_time_ms'}, inplace=True)

        return top_50.to_dict(orient='records')
    
    @staticmethod
    def top_50_countries(request_logs):
        """
        Get the top 50 countries based on request count, only grouping non-null and non-empty country names.
        """
        # Filter out null or empty country_name
        filtered_logs = request_logs[request_logs['country_name'].notnull() & (request_logs['country_name'].astype(str).str.strip() != '')]

        if 'country_code' in filtered_logs.columns:
            top_country = (
                filtered_logs
                .groupby(['country_name', 'country_code'])
                .size()
                .sort_values(ascending=False)
                .reset_index()
                .head(50)
            )
            top_country.columns = ['country_name', 'country_code', 'value']
        else:
            top_country = (
                filtered_logs
                .groupby(['country_name'])
                .size()
                .sort_values(ascending=False)
                .reset_index()
                .head(50)
            )
            top_country.columns = ['country_name', 'value']

        return top_country.to_dict(orient='records')
    
    @staticmethod
    def top_50_errors(request_logs):
        """
        Get the top 50 errors based on status code and error message.
        """
        recently_errors = request_logs[request_logs['status_code'] >= 400][['id', 'path', 'method', 'status_code', 'error_message', 'created_at', 'app_name']].sort_values(by='created_at', ascending=False).head(50)
        return recently_errors.to_dict(orient='records')

    def compute_top_50s_parallel(self, logs):
        """
        Compute the top 50 slowest routes, countries, and errors in parallel using ThreadPoolExecutor.
        """

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_routes = executor.submit(self.top_50_slowest_routes, logs)
            future_country = executor.submit(self.top_50_countries, logs)
            future_errors = executor.submit(self.top_50_errors, logs)

            return {
                'top_50_slowest_routes': future_routes.result(),
                'top_50_countries': future_country.result(),
                'top_50_errors': future_errors.result(),
            }

    @staticmethod
    def build_grouped_data_table(request_logs):
        """
        Build grouped data table by unique path and aggregate the data to get count, average response_time, and list of methods.
        """
        grouped_data = request_logs.groupby('path').agg(
            methods=('method', lambda x: list(x.unique())),
            avg_process_time_ms=('process_time_ms', lambda x: round(x.mean(), 4)),
            min_process_time_ms=('process_time_ms', lambda x: round(x.min(), 4)),
            max_process_time_ms=('process_time_ms', lambda x: round(x.max(), 4)),
            status_codes=('status_code', lambda x: sorted(list(x.unique()))),
            last_activity=('created_at', 'max'),
            count=('path', 'count'),  # count of rows per path
            success_count=('status_code', lambda x: len(x[x < 400])),
            client_error_count=('status_code', lambda x: len(x[(x >= 400) & (x < 500)])),
            server_error_count=('status_code', lambda x: len(x[x >= 500])),
        ).reset_index()

        # Sort the grouped data by created_at in descending order
        grouped_data.sort_values(by='count', ascending=False, inplace=True)

        return grouped_data.to_dict(orient='records')

    @staticmethod
    def build_response(
        filters=None, general=None,
        time_chart=None, app_chart=None, status_code_chart=None, request_method_chart=None,
        top_50_slowest_routes=None, top_50_countries=None, top_50_errors=None,
        data_table=None, status=HTTP_200_OK, **kwargs
    ):
        """
        Build a dynamic response with the provided parameters. 
        """
        filters = filters or {}
        general = general or {}
        time_chart = time_chart or {}
        app_chart = app_chart or {}
        status_code_chart = status_code_chart or {}
        request_method_chart = request_method_chart or {}
        data_table = data_table or {}

        return Response({
            **kwargs,
            'filters': {
                'start_date': filters.get('start_date'),
                'end_date': filters.get('end_date'),
                'status_code': filters.get('status_code'),
                'request_method': filters.get('request_method'),
                'application_name': filters.get('application_name'),
            },
            'statistics': {
                'total_requests': general.get('total_requests', 0),
                'success_requests': general.get('success_requests', 0),
                'client_error_requests': general.get('client_error_requests', 0),
                'server_error_requests': general.get('server_error_requests', 0),
                'success_rate': general.get('success_rate', "0%"),
                'client_error_rate': general.get('client_error_rate', "0%"),
                'server_error_rate': general.get('server_error_rate', "0%"),
                'avg_process_time_ms': general.get('avg_process_time_ms', 0)
            },
            'time_chart': {
                'categories': time_chart.get('categories', []),
                'request_series': time_chart.get('request_series', []),
                'response_time_series': time_chart.get('response_time_series', [])
            },
            'app_chart': {
                'categories': app_chart.get('categories', []),
                'series': app_chart.get('series', [])
            },
            'status_code_chart': {
                'categories': status_code_chart.get('categories', []),
                'series': status_code_chart.get('series', [])
            },
            'request_method_chart': {
                'categories': request_method_chart.get('categories', []),
                'series': request_method_chart.get('series', [])
            },
            'top_50_slowest_routes': top_50_slowest_routes or [],
            'top_50_countries': top_50_countries or [],
            'top_50_errors': top_50_errors or [],
            'data_table': data_table.get('data_table', []) if isinstance(data_table, dict) else []
        }, status=status)


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
                        'name': 'Response Time (s)',
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

        
        request_logs = self.get_all_requestlogs(role=request.user.role.id, start_date=start_date, end_date=end_date, application_name=application_name, status_code=status_code, request_method=request_method)

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
        status_code_categories = sorted(request_logs[request_logs['status_code'] >= 400]['status_code'].unique())
        status_code_series = [
            {
                'name': app_name,
                'data': request_logs[(request_logs['app_name'] == app_name) & (request_logs['status_code'] >= 400)].groupby('status_code').size().reindex(status_code_categories).fillna(0).tolist()
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

        # Top visitors by country
        if 'country_code' in request_logs.columns:
            top_country = request_logs.groupby(['country_name', 'country_code']).size().sort_values(ascending=False).reset_index()
            top_country.columns = ['country_name', 'country_code', 'value']
        else:
            top_country = request_logs.groupby(['country_name']).size().sort_values(ascending=False).reset_index()
            top_country.columns = ['country_name', 'value']

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
                        'name': 'Response Time (s)',
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
            'top_country': top_country.to_dict(orient='records'),
            'recently_errors': recently_errors.to_dict(orient='records'),
            'data_table': df
        }, status=HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='overview2')
    def get_temp(self, request):
        start_time = pd.Timestamp.now('Asia/Jakarta')
        print(f"User logged in: {request.user}")
        try:
            start_date = pd.to_datetime(request.data.get('start_date', pd.Timestamp.now(tz='Asia/Jakarta') - pd.Timedelta(days=self.DEFAULT_DATE_RANGE))).tz_convert('Asia/Jakarta')
            end_date = pd.to_datetime(request.data.get('end_date', pd.Timestamp.now(tz='Asia/Jakarta'))).tz_convert('Asia/Jakarta')
        except ValueError:
            raise ValidationException("Invalid start_date or end_date format")

        if start_date > end_date:
            raise ValidationException("start_date must be less than end_date")
        
        status_code = request.data.get('status_code', None)
        application_name = request.data.get('application_name', None)
        request_method = request.data.get('request_method', None)

        freq, start_date, end_date, complete_date_range = self.determine_frequency_and_range(start=start_date, end=end_date)

        # ========== Get All Request Logs ==========
        request_logs = self.get_all_requestlogs(
            role=request.user.role.id,
            start_date=start_date, 
            end_date=end_date, 
            application_name=application_name, 
            status_code=status_code, 
            request_method=request_method
            )
        
        # Check if request_logs is empty
        if request_logs.empty:
            return self.build_response(
                execution_time=(pd.Timestamp.now('Asia/Jakarta') - start_time).total_seconds(),
                filters={
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'status_code': status_code,
                    'request_method': request_method,
                    'application_name': application_name,
                }
            )

        # ========== Sort Request Logs ==========
        request_logs.sort_values(by='created_at', inplace=True)

        # ========== Time Index ==========
        time_index = pd.Grouper(key='created_at', freq=freq, origin=start_date)

        # ========== Grouping Data ==========
        time_chart = self.build_time_chart(request_logs, complete_date_range, time_index)
        app_chart = self.build_app_chart(request_logs)
        status_code_chart = self.build_status_code_chart(request_logs)
        request_method_chart = self.build_request_method_chart(request_logs)

        # ========== Summary Statistics ==========
        summary_stats = self.build_summary_stats(request_logs)

        # ========== Top 50 ==========
        top_50s = self.compute_top_50s_parallel(request_logs)

        # ========== Top 50 Slowest Routes ==========
        # top_50_slowest_route = self.top_50_slowest_routes(request_logs)
        # top_50_countries = self.top_50_countries(request_logs)
        # top_50_errors = self.top_50_errors(request_logs)

        # ========== Grouped Data Table ==========
        grouped_data_table = self.build_grouped_data_table(request_logs)

        return self.build_response(
            execution_time=(pd.Timestamp.now('Asia/Jakarta') - start_time).total_seconds(),
            filters={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'status_code': status_code,
                'request_method': request_method,
                'application_name': application_name,
            },
            general=summary_stats,
            time_chart=time_chart,
            app_chart=app_chart,
            status_code_chart=status_code_chart,
            request_method_chart=request_method_chart,
            top_50_slowest_routes=top_50s['top_50_slowest_routes'],
            top_50_countries=top_50s['top_50_countries'],
            top_50_errors=top_50s['top_50_errors'],
            data_table={
                'data_table': grouped_data_table
            },
        )

    @action(detail=False, methods=['POST'], url_path='data-table-by-path')
    def get_data_table_by_path(self, request):
        """
        Return a list of all request logs with pagination.
        """
        try:
            start_date = pd.to_datetime(request.data.get('start_date', pd.Timestamp.now(tz='Asia/Jakarta') - pd.Timedelta(days=self.DEFAULT_DATE_RANGE))).tz_convert('Asia/Jakarta')
            end_date = pd.to_datetime(request.data.get('end_date', pd.Timestamp.now(tz='Asia/Jakarta'))).tz_convert('Asia/Jakarta')
        except ValueError:
            return Response({'error': 'Invalid start_date format'}, status=HTTP_400_BAD_REQUEST)

        application_name = request.data.get('application_name', None)
        status_code = request.data.get('status_code', None)
        request_method = request.data.get('request_method', None)

        path = request.data.get('path', None)

        request_logs = self.get_all_requestlogs(role=request.user.role.id, start_date=start_date, end_date=end_date, 
                                                application_name=application_name, status_code=status_code, 
                                                request_method=request_method, path=path)
        
        if request_logs.empty:
            return Response({
                'filters': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'path': path,
                },
                'data_table': []
            }, status=HTTP_200_OK)
        time.sleep(2)
        return Response({
            'filters': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'path': path,
            },
            'data_table': request_logs.sort_values(by='created_at', ascending=False).to_dict(orient='records')
        }, status=HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='data-table')
    def get_data_table(self, request):
        """
        Return a list of all request logs with pagination.
        """
        try:
            start_date = pd.to_datetime(request.data.get('start_date', pd.Timestamp.now(tz='Asia/Jakarta') - pd.Timedelta(days=1))).tz_convert('Asia/Jakarta')
            end_date = pd.to_datetime(request.data.get('end_date', pd.Timestamp.now(tz='Asia/Jakarta'))).tz_convert('Asia/Jakarta')
        except ValueError:
            return Response({'error': 'Invalid start_date format'}, status=HTTP_400_BAD_REQUEST)

        status_code = request.data.get('status_code', None)
        application_name = request.data.get('application_name', None)
        request_method = request.data.get('request_method', None)

        request_logs = self.get_all_requestlogs(role=request.user.role.id, start_date=start_date, end_date=end_date, application_name=application_name, status_code=status_code, request_method=request_method)
        
        # ========== Grouping Data ==========
        # Group by unique status_code and count the number of occurrences
        status_code_counts = request_logs['status_code'].value_counts().reset_index()

        # Group by unique request_method and count the number of occurrences
        request_method_counts = request_logs['method'].value_counts().reset_index()

        # Group by application name and count the number of occurrences
        app_name_counts = request_logs['app_name'].value_counts().reset_index()

        data_table = request_logs.sort_values(by='created_at', ascending=False).to_dict(orient='records')

        # Apply pagination only to the data_table
        # paginator = PageNumberPagination()
        # paginator.page_size = 10  # Set the page size
        # paginated_logs = paginator.paginate_queryset(data_table, request)

        return Response({
            'filters': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'status_code': status_code,
                'request_method': request_method,
                'application_name': application_name,
            },
            'status_code_counts': status_code_counts.to_dict(orient='records'),
            'request_method_counts': request_method_counts.to_dict(orient='records'),
            'app_name_counts': app_name_counts.to_dict(orient='records'),
            'data_table': data_table
            # 'data_table': {
            #     'previous': paginator.get_previous_link(),
            #     'next': paginator.get_next_link(),
            #     'count': paginator.page.paginator.count,
            #     'results': paginated_logs
            # }
        })