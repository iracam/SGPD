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
node docs/operacao/build.mjs

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

step "Reinício do serviço"
sudo systemctl restart "$service_name"

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
