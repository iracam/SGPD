"""Uniform error envelope for the SGPD API.

Every error response carries ``{"code", "message"}`` and, when the failure is
per-field, a ``"details"`` mapping. The SPA depends on ``code`` for control flow
and on ``details`` to place messages next to form fields.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

NON_FIELD_ERRORS = "non_field_errors"


def api_error(
    *,
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> Response:
    payload: dict[str, Any] = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return Response(payload, status=status_code)


def _django_validation_details(error: DjangoValidationError) -> dict[str, Any]:
    # ``message_dict`` raises AttributeError when the error carries a plain list,
    # which is how ``validate_password`` and non-field service errors arrive.
    if hasattr(error, "message_dict"):
        return {field: list(messages) for field, messages in error.message_dict.items()}
    return {NON_FIELD_ERRORS: list(error.messages)}


def _drf_validation_details(detail: Any) -> dict[str, Any]:
    if isinstance(detail, dict):
        return dict(detail)
    if isinstance(detail, list):
        return {NON_FIELD_ERRORS: detail}
    return {NON_FIELD_ERRORS: [detail]}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Translate every known failure into the envelope, keeping 500 opaque."""

    # Services raise Django's ValidationError, which DRF does not handle on its
    # own and would otherwise surface as an unhandled 500.
    if isinstance(exc, DjangoValidationError):
        return api_error(
            code="validation_error",
            message="Os dados enviados são inválidos.",
            status_code=400,
            details=_django_validation_details(exc),
        )
    if isinstance(exc, DjangoPermissionDenied):
        return api_error(
            code="permission_denied",
            message="Usuário sem permissão para esta operação.",
            status_code=403,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        # Unexpected failure: let Django log it and return an opaque 500 rather
        # than leaking the exception to the client.
        return None

    if isinstance(exc, exceptions.NotAuthenticated):
        # APIView.handle_exception downgrades this to 403 because
        # SessionAuthentication publishes no WWW-Authenticate header. The SPA
        # needs 401 to distinguish "log in" from "you may not do this".
        return api_error(
            code="not_authenticated",
            message="Autenticação necessária.",
            status_code=401,
        )
    if isinstance(exc, exceptions.AuthenticationFailed):
        return api_error(
            code="authentication_failed",
            message="Credenciais inválidas ou sessão expirada.",
            status_code=401,
        )
    if isinstance(exc, exceptions.ValidationError):
        return api_error(
            code="validation_error",
            message="Os dados enviados são inválidos.",
            status_code=400,
            details=_drf_validation_details(exc.detail),
        )
    if isinstance(exc, exceptions.PermissionDenied):
        return api_error(
            code="permission_denied",
            message=str(exc.detail),
            status_code=403,
        )
    if isinstance(exc, Http404 | exceptions.NotFound):
        return api_error(
            code="not_found",
            message="Recurso não encontrado.",
            status_code=404,
        )
    if isinstance(exc, exceptions.MethodNotAllowed):
        return api_error(
            code="method_not_allowed",
            message="Método não permitido para este recurso.",
            status_code=405,
        )
    if isinstance(exc, exceptions.Throttled):
        throttled = api_error(
            code="throttled",
            message="Muitas tentativas. Aguarde antes de tentar novamente.",
            status_code=429,
        )
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            throttled.headers["Retry-After"] = retry_after
        return throttled

    detail = getattr(exc, "detail", None)
    return api_error(
        code=str(getattr(detail, "code", "error")),
        message=str(detail) if detail is not None else "Não foi possível concluir a operação.",
        status_code=response.status_code,
    )
