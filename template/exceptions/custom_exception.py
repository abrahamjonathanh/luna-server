import traceback

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

    return response