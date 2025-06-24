# user_threading_util.py
"""
Utils for storing/accessing something within a local thread.
These utils are usually used, but not limited to, middlewares.
"""

from threading import local

from request_log.models.request_log_model import RequestLog

_local_thread = local()


def get_current_user() -> str:
    """
    Returns current thread's `user`.
    Guaranteed to always return string (including empty)
    """
    return getattr(_local_thread, "user", "")


def set_current_user(user: str) -> None:
    """
    Set current thread's `user`
    """
    assert isinstance(user, str), "`user` must be string"
    _local_thread.user = user


def get_current_request_log() -> "RequestLog | None":
    """
    Returns current thread's `request_log`,
    either `RequestLog` instance or `None`

    Used in log 500 middleware
    """
    return getattr(_local_thread, "request_log", None)


def set_current_request_log(request_log: RequestLog):
    """
    Set current thread's `request_log`. Used in request log middleware
    """
    assert isinstance(
        request_log, RequestLog
    ), "`request_log` must be `RequestLog` instance"
    _local_thread.request_log = request_log


# functions below are not used in template, but exists in other apps. for reference only


def get_current_user_id() -> int:
    """
    Returns current thread's `user_id`.
    Guaranteed to always return int (including 0 if invalid)
    """
    return getattr(_local_thread, "user_id", 0)


def set_current_user_id(user_id: "int | str") -> None:
    """
    Set current thread's `user_id`
    """
    assert isinstance(user_id, (int, str)), "`user_id` must be `int` or `str`"
    _local_thread.user_id = str(user_id)


def get_current_request():
    """
    Returns current thread's `request`

    Commonly used to get `delete_reason` when doing
    soft-delete (if needed, based on requirement)
    """
    return getattr(_local_thread, "request", None)


def set_current_request(request):
    """
    Set current thread's `request`

    Commonly used to get current request from incoming request
    """
    _local_thread.request = request


def get_current_role() -> str:
    """
    Returns current thread's `role`.
    Guaranteed to always return string (including empty)
    """
    return getattr(_local_thread, "role", "")


def set_current_role(role: str) -> None:
    """
    Set current thread's `role`
    """
    assert isinstance(role, str), "`role` must be string"
    _local_thread.role = role