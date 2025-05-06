import traceback

from rest_framework.response import Response
from rest_framework.views import exception_handler
from template.utils.threading import get_current_request_log

def custom_exception_handler(exc, context):
    # Call the default exception handler to get the standard error response
    response = exception_handler(exc, context)

    # Retrieve the current request log to record the error message
    req_log = get_current_request_log()
    if req_log is not None:
        trace_back = traceback.format_exc()
        error_message = f"{str(exc)}\n\n{trace_back}"

        if req_log.error_message != error_message:
            req_log.error_message = error_message
            req_log.save()
        req_log.save()

        # Customize the error response
        custom_response = {
            'message': 'Request failed',
            'detail': response.data,
            'status_code': response.status_code
        }
        # Add additional fields if they exist in the exception
        if hasattr(exc, 'message'):
            custom_response['message'] = str(exc.message)
        if hasattr(exc, 'detail'):
            custom_response['detail'] = str(exc.detail)
        
        return Response(custom_response, status=response.status_code)

    return response