#!/usr/bin/env bash
#
# Deploy do SGPD no host publicado (ADR-055).
#
# Executado à mão no próprio host: não há CI/CD e a validação continua local
# (ADR-016). O script é idempotente — rodar de novo sobre a mesma referência não
# muda nada além de reconstruir artefatos.
#
# O que ele NÃO faz, por decisão:
#   - aplicar migration. `AGENTS.md` §9 e `RUNBOOK.md` §8 exigem revisar o SQL
#     Oracle antes; aqui o script apenas detecta pendência e para;
#   - provisionar o host. Usuário, diretórios, venv, units e `.env` são feitos
#     uma vez, conforme o `RUNBOOK.md` §11.
#
# Uso:
#   scripts/deploy.sh [referência git]     # padrão: origin/main

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_root=$(cd -- "$script_dir/.." && pwd)
target_ref="${1:-origin/main}"
service_name="${SGPD_SERVICE_NAME:-sgpd-web}"
health_base="${SGPD_HEALTH_BASE_URL:-https://sgpd.bsabioenergia.com.br}"
# Worker e Beat sobem com o mesmo código do web (ADR-057). Reiniciar só o web
# deixaria o worker rodando a versão anterior das tarefas.
async_services=("sgpd-celery-worker" "sgpd-celery-beat")

cd "$project_root"

step() {
    printf '\n== %s\n' "$1"
}

if [[ ! -r "$project_root/.env" ]]; then
    echo "Arquivo .env não encontrado ou sem permissão de leitura." >&2
    exit 2
fi

step "Código: $target_ref"
git fetch --tags --prune origin
git checkout --detach "$target_ref"
git --no-pager log -1 --oneline

step "Dependências Python"
# --frozen: instala exatamente o uv.lock versionado, sem reresolver.
uv sync --frozen --no-dev

step "Build da SPA"
npm --prefix frontend ci
npm --prefix frontend run build

step "Manuais operacionais (ADR-053)"
# `--html`: é o `.html` que o `/ajuda/<slug>/` serve. O PDF é entrega para
# humanos, ninguém o pede ao host, e gerá-lo abriria o Chromium por nada.
node docs/operacao/build.mjs --html

step "Estáticos"
uv run manage.py collectstatic --noinput

step "Migrations"
if ! uv run manage.py migrate --check >/dev/null 2>&1; then
    cat >&2 <<'EOF'
Há migration pendente. O deploy para aqui por decisão.

Revise o SQL Oracle antes de aplicar (RUNBOOK.md §8):

    uv run manage.py showmigrations --plan | grep '\[ \]'
    uv run manage.py sqlmigrate <app> <numero>
    uv run manage.py migrate <app>

Depois de aplicar, rode este script de novo.
EOF
    exit 3
fi
echo "Nenhuma migration pendente."

step "Postura de segurança"
uv run manage.py check --deploy

step "Redis"
# O Redis é do host e compartilhado (ADR-057): o deploy não o sobe, só confere
# que está lá. Sem ele o cache não responde, `readiness` falha e as tarefas
# ficam sem broker — melhor descobrir aqui do que depois de reiniciar.
# `manage.py shell` e não `python -c`: o módulo de settings vem do `.env` pelo
# bootstrap do projeto, e reproduzi-lo aqui daria duas fontes para a mesma
# decisão.
if ! uv run manage.py shell -c '
import sys

from django.core.cache import cache

try:
    cache.set("deploy-probe", "ok", timeout=30)
    sys.exit(0 if cache.get("deploy-probe") == "ok" else 1)
except Exception as failure:
    print(failure, file=sys.stderr)
    sys.exit(1)
'; then
    echo "Redis não respondeu. Confira o container do host e SGPD_REDIS_URL no .env." >&2
    exit 4
fi
echo "Redis respondendo."

step "Reinício dos serviços"
sudo systemctl restart "$service_name"
for unit in "${async_services[@]}"; do
    sudo systemctl restart "$unit"
done

step "Saúde"
# Sempre pela URL publicada: em HTTP puro o navegador descarta o cookie Secure e
# o login não completa, então é isso que precisa responder.
for probe in live ready; do
    printf '  /health/%s/ ... ' "$probe"
    curl -fsS --max-time 15 "$health_base/health/$probe/" >/dev/null
    echo 'ok'
done

step "Concluído"
systemctl --no-pager --lines=0 status "$service_name" || true
for unit in "${async_services[@]}"; do
    systemctl --no-pager --lines=0 status "$unit" || true
done
