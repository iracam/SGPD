import logging
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError, connection
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

#: Manuais operacionais publicáveis, por slug. A lista é branca de propósito: o
#: caminho no disco nunca é montado a partir da URL, então não há travessia
#: possível por mais criativo que seja o pedido.
OPERATION_MANUALS: dict[str, str] = {
    "responsaveis-de-area": "Manual do Responsável de Área",
    "departamento-pessoal": "Manual do Departamento Pessoal",
    "grupos-templates-regras": "Manual de Configuração",
}

SPA_LOGIN_PATH = "/fe/login"


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


@require_GET
def manual(request: HttpRequest, slug: str) -> HttpResponse:
    """Serve um manual operacional de `docs/operacao/` para sessão autenticada.

    O arquivo não vai para o bundle do Angular de propósito: o WhiteNoise serve
    a raiz do build sem autenticação, e estes documentos descrevem o processo
    interno inteiro. Servindo por aqui, o mesmo cookie de sessão da SPA vale
    para a aba nova e o `.md` continua sendo a fonte única.
    """

    # Autenticação antes do 404: responder "não existe" a quem não entrou
    # revelaria quais manuais existem.
    if not request.user.is_authenticated:
        return redirect(SPA_LOGIN_PATH)

    if slug not in OPERATION_MANUALS:
        raise Http404("Manual inexistente.")

    caminho: Path = settings.OPERATION_MANUALS_DIR / f"{slug}.html"
    if not caminho.is_file():
        logger.warning("manual operacional ausente em %s", caminho)
        return HttpResponse(
            "Manual não gerado. Execute `node docs/operacao/build.mjs`.",
            content_type="text/plain; charset=utf-8",
            status=503,
        )

    response = HttpResponse(caminho.read_bytes(), content_type="text/html; charset=utf-8")
    # Revalida sempre: o arquivo é regerado pelo build da documentação e uma
    # cópia velha no navegador ensinaria o procedimento errado.
    response["Cache-Control"] = "private, no-cache"
    return response
