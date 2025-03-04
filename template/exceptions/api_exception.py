from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status


def get_error_format(status_code, title, message, error_code, detail={}):
    return {
        "status_code": status_code,  # default http code
        "title": title,  # popup title on FE
        "message": message,  # popup content on FE, bisa string bisa dict
        "error_code": error_code,  # custom error code of our own
        "detail": detail,  # further detail on error
    }


class ErrorCode:
    """
    An ever-growing collection of static error codes,
    each denoting an error scenario that may arise during development
    """

    # general format: PA_OPTIONAL_CATEGORY_YOUR_ERROR
    # e.g.: PA_EXCEL_MISSING_SHEET (PA_category_error), PA_NOT_FOUND (PA_error)
    _DELIMITER = ""
    _PREFIX = "PA" + _DELIMITER  # "PA"

    UNHANDLED = _PREFIX + "UNHANDLED"  # "PA_UNHANDLED"
    VALIDATION_ERROR = _PREFIX + "VALIDATION_ERROR"  # "PA_VALIDATION_ERROR"
    NOT_FOUND = _PREFIX + "NOT_FOUND"  # "PA_NOT_FOUND"
    FORBIDDEN = _PREFIX + "FORBIDDEN"  # "PA_FORBIDDEN"
    NOT_AUTHENTICATED = _PREFIX + "NOT_AUTHENTICATED"  # PA_NOT_AUTHENTICATED
    AUTHENTICATION_FAILED = (
        _PREFIX + "AUTHENTICATION_FAILED"
    )  # PA_AUTHENTICATION_FAILED
    METHOD_NOT_ALLOWED = _PREFIX + "METHOD_NOT_ALLOWED"  # PA_METHOD_NOT_ALLOWED
    NOT_ACCEPTABLE = _PREFIX + "NOT_ACCEPTABLE"  # PA_NOT_ACCEPTABLE

    _CRYPTOGRAPHY = _PREFIX + "CRYPTOGRAPHY" + _DELIMITER
    ENCRYPT_ERROR = _CRYPTOGRAPHY + "ENCRYPT_ERROR"
    DECRYPT_ERROR = _CRYPTOGRAPHY + "DECRYPT_ERROR"

    _REQUEST = _PREFIX + "REQUEST" + _DELIMITER
    REQUEST_MISSING_KEY = _REQUEST + "MISSING_KEY"
    REQUEST_INVALID_VALUE = _REQUEST + "INVALID_VALUE"


class CustomAPIException(exceptions.APIException):
    """
    A custom exception class that acts as a
    base exception for all custom exception classes.
    This also becomes the standardised http error 500 class to raise
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_title = _("Internal Server Error")  # for popup title on FE
    default_message = _("A server error occurred.")
    default_error_code = ErrorCode.UNHANDLED

    def _init_(
        self,
        title: str = None,
        message: str = None,
        error_code: str = None,
        detail: dict = {},
    ):
        if title is None:
            title = self.default_title
        if message is None:
            message = self.default_message
        if error_code is None:
            error_code = self.default_error_code

        self.detail = get_error_format(
            self.status_code,
            title,
            message,
            error_code,
            detail,
        )


class ValidationErrorException(CustomAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_title = _("Validation Error")
    default_message = _("Validation error. Please recheck your input.")
    default_error_code = ErrorCode.VALIDATION_ERROR


class NotFoundException(CustomAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_title = _("Not found")
    default_message = _("The resource you are looking for cannot be found")
    default_error_code = ErrorCode.NOT_FOUND