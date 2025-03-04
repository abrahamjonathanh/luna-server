from django.http.response import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.views import exception_handler

from template.exceptions.api_exception import ErrorCode, get_error_format


def custom_exception_handler(exc, context):
    # to get the standard error response.
    response = exception_handler(exc, context)

    # edit the response to our own custom format
    if isinstance(exc, exceptions.ValidationError):
        response.data = get_error_format(
            status_code=response.status_code,
            title=_("Validation error. Please recheck your input."),
            message=_get_detail(response),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    elif isinstance(exc, exceptions.NotAuthenticated):
        response.data = get_error_format(
            status_code=response.status_code,
            title=_("Not Authenticated"),
            message=_get_detail(response),
            error_code=ErrorCode.NOT_AUTHENTICATED,
        )
    elif isinstance(exc, exceptions.AuthenticationFailed):
        response.data = get_error_format(
            status_code=response.status_code,
            title=_("Authentication Failed"),
            message=_get_detail(response),
            error_code=ErrorCode.AUTHENTICATION_FAILED,
        )
    elif isinstance(exc, exceptions.PermissionDenied):
        response.data = get_error_format(
            status_code=response.status_code,
            title=_("Permission Denied"),
            message=_get_detail(response),
            error_code=ErrorCode.FORBIDDEN,
        )
    elif isinstance(exc, exceptions.NotFound) or isinstance(exc, Http404):
        response.data = get_error_format(
            status_code=response.status_code,
            title=_("Not Found"),
            message=_get_detail(response),
            error_code=ErrorCode.NOT_FOUND,
        )
    elif isinstance(exc, exceptions.MethodNotAllowed):
        response.data = get_error_format(
            status_code=response.status_code,
            title=_("Method Not Allowed"),
            message=_get_detail(response),
            error_code=ErrorCode.METHOD_NOT_ALLOWED,
        )
    elif isinstance(exc, exceptions.NotAcceptable):
        response.data = get_error_format(
            status_code=response.status_code,
            title=_("Not Acceptable"),
            message=_get_detail(response),
            error_code=ErrorCode.NOT_ACCEPTABLE,
        )

    return response


def _get_detail(response):
    try:
        message = _(str(response.data["message"]))
    except Exception:
        message = response.data

    return message