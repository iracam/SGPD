import logging
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
def liveness(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_GET
def readiness(request: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM DUAL")
            row = cursor.fetchone()
    except DatabaseError:
        logger.warning("database readiness check failed")
        return JsonResponse({"status": "unavailable"}, status=503)

    if row != (1,):
        logger.warning("database readiness check returned an unexpected result")
        return JsonResponse({"status": "unavailable"}, status=503)

    return JsonResponse({"status": "ok"})


@require_GET
@ensure_csrf_cookie
def spa(request: HttpRequest) -> HttpResponse:
    """Serve the Angular shell and seed the CSRF cookie on first load.

    Every non-API route lands here; the client-side router decides what to
    render. WhiteNoise serves the hashed assets from the same directory.
    """

    index: Path = settings.FRONTEND_INDEX
    if not index.is_file():
        logger.warning("frontend bundle is missing at %s", index)
        return HttpResponse(
            "Interface não construída. Execute `npm ci && npm run build` em frontend/.",
            content_type="text/plain; charset=utf-8",
            status=503,
        )

    response = HttpResponse(index.read_bytes(), content_type="text/html; charset=utf-8")
    # The asset URLs inside change on every build; never let a proxy pin them.
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response
