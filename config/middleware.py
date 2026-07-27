"""Request correlation middleware."""

import re
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")
_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class CorrelationIdMiddleware:
    header_name = "X-Correlation-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        supplied = request.headers.get(self.header_name, "")
        request_id = supplied if _SAFE_CORRELATION_ID.fullmatch(supplied) else str(uuid.uuid4())
        token = correlation_id.set(request_id)

        try:
            response = self.get_response(request)
            response[self.header_name] = request_id
            return response
        finally:
            correlation_id.reset(token)
