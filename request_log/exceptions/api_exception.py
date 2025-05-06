from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status

class CustomAPIException(exceptions.APIException):
    """
    Base class for custom API exceptions
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A server error occurred.'
    default_message = 'Request failed'

    def __init__(self, detail=None, message=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        if message is not None:
            self.message = message
        else:
            self.message = self.default_message
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail
        super().__init__(detail=self.detail)


class NotFoundException(CustomAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = 'Resource not found'
    default_detail = 'The requested resource was not found.'


class ValidationException(CustomAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = 'Validation error'
    default_detail = 'One or more validation errors occurred.'


class UnauthorizedException(CustomAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = 'Unauthorized'
    default_detail = 'Authentication credentials were not provided or are invalid.'