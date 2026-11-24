"""Domain errors raised by the service layer; main.py maps them to HTTP responses."""
from __future__ import annotations


class NaviError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFound(NaviError):
    status_code = 404


class Forbidden(NaviError):
    status_code = 403


class Conflict(NaviError):
    status_code = 409


class Invalid(NaviError):
    status_code = 422


class TooLarge(NaviError):
    status_code = 413


class Upstream(NaviError):
    """A site Navi fetched from (e.g. Linktree) failed or sent something unreadable."""

    status_code = 502
