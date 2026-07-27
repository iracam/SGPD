import logging

from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse
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
