#!/usr/bin/env bash
#
# Recompõe o banco do SGPD a partir das fixtures de configuração.
#
# Quatro passos, nesta ordem:
#   1. exporta as fixtures 01..06 do estado atual para `docs/fixtures/`;
#   2. guarda um despejo integral com data no nome — o operacional inclusive;
#   3. esvazia todas as tabelas do Django;
#   4. recarrega só as fixtures e reacerta as sequências.
#
# É DESTRUTIVO e não tem volta pela aplicação: o passo 3 apaga processo,
# snapshot, tarefa, checklist, pendência, evidência, notificação, exportação,
# idempotência, sessão e as três trilhas de auditoria. Auditoria é append-only
# (`AGENTS.md`): recompor o banco é ato de ambiente, não operação de rotina. O
# despejo do passo 2 é a única volta, e é manual.
#
# O `.env` deste host aponta para o mesmo Oracle que a aplicação publicada usa
# (ADR-055): leia o alvo que o script imprime antes de confirmar.
#
# O que ele NÃO faz, por decisão:
#   - aplicar migration. Exige revisão do SQL Oracle antes (`AGENTS.md` §9,
#     `RUNBOOK.md` §8); aqui o script só detecta pendência e para. Carregar
#     fixture em schema defasado falharia no meio, já com o banco vazio;
#   - parar a aplicação. As units `sgpd-web`, `sgpd-celery-worker` e
#     `sgpd-celery-beat` vivem no host publicado, não aqui — pare-as lá antes,
#     ou uma requisição no meio do passo 3 pega o banco pela metade;
#   - mexer no storage privado de evidência. Os bytes ficam fora do banco
#     (`RUNBOOK.md` §6): depois da carga, arquivo sem linha é lixo, e apagá-lo
#     é decisão de quem sabe se aquele acervo importa;
#   - limpar o Redis. O cache guarda só o batimento do agendamento e a sonda de
#     readiness; apagá-lo faria a sonda de operação acusar agendamento parado
#     sem que nada tivesse parado. A fila do broker também fica: quem sobrou
#     nela aponta para notificação que deixou de existir, e
#     `dispatch_notification` já trata alvo ausente como resultado legítimo;
#   - versionar nada. `docs/fixtures/` é ignorada pelo git de propósito: o
#     retrato traz nome, e-mail e vínculo de gente real.
#
# Uso:
#   scripts/reset_from_fixtures.sh                 # pede confirmação
#   scripts/reset_from_fixtures.sh --yes           # sem confirmação
#   scripts/reset_from_fixtures.sh --export-only   # passos 1 e 2, nada é apagado
#   scripts/reset_from_fixtures.sh --keep-fixtures # pula o 1: carrega o que já está lá

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_root=$(cd -- "$script_dir/.." && pwd)
fixtures_dir="$project_root/docs/fixtures"
stamp=$(date +%Y%m%d-%H%M%S)
backup_json="$fixtures_dir/_backup_completo_$stamp.json"

assume_yes=0
export_only=0
keep_fixtures=0

for argument in "$@"; do
    case "$argument" in
        --yes | -y) assume_yes=1 ;;
        --export-only) export_only=1 ;;
        --keep-fixtures) keep_fixtures=1 ;;
        -h | --help)
            sed -n '2,/^set -euo/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//; $d'
            exit 0
            ;;
        *)
            echo "Argumento desconhecido: $argument (use --help)" >&2
            exit 2
            ;;
    esac
done

cd "$project_root"

step() {
    printf '\n== %s\n' "$1"
}

# Contagem por modelo, antes e depois. É o que permite conferir de olho que a
# carga repôs a configuração inteira e que o operacional saiu.
report_counts() {
    uv run manage.py shell --no-imports -c '
from django.apps import apps

total = 0
for model in sorted(apps.get_models(), key=lambda model: model._meta.label):
    count = model.objects.count()
    total += count
    if count:
        print(f"  {model._meta.label:52} {count:>6}")
label = "TOTAL"
print(f"  {label:52} {total:>6}")
'
}

# As fixtures 01..06 são o retrato da configuração: contas, papéis, setores,
# central e catálogo de workflow. Processo, tarefa, pendência, evidência,
# notificação e auditoria ficam fora por serem operacionais — semente não
# carrega trilha. A ordem numérica é a ordem de carga, e os dois vetores abaixo
# andam juntos pelo índice.
fixture_names=(
    01_users
    02_roles
    03_sectors
    04_sector_responsibles
    05_system_settings
    06_workflow_config
)

fixture_models=(
    "accounts.user"
    "accounts.role accounts.roleassignment"
    "sectors.validationsector sectors.sectorscope"
    "sectors.sectorresponsible"
    "system_settings.ldapconfiguration system_settings.emailconfiguration"
    "templates_engine.checklisttemplate
     templates_engine.checklisttemplateversion
     templates_engine.checklisttemplateitem
     templates_engine.validationgroup
     templates_engine.validationgroupversion
     templates_engine.validationgroupsector
     templates_engine.groupapplicabilityrule"
)

fixture_files=()
for name in "${fixture_names[@]}"; do
    fixture_files+=("docs/fixtures/$name.json")
done

# Sai do despejo integral: `contenttypes` e `auth.permission` são recriadas pelo
# próprio `flush` (sinal `post_migrate`) com PK nova, e é por isso que tudo é
# despejado com `--natural-foreign` — quem aponta para permissão aponta por
# chave natural e sobrevive à troca. `sessions` é transitória e `admin.logentry`
# é trilha do admin somente leitura.
backup_excludes=(
    --exclude contenttypes
    --exclude auth.permission
    --exclude sessions
    --exclude admin.logentry
)

if [[ ! -r "$project_root/.env" ]]; then
    echo "Arquivo .env não encontrado ou sem permissão de leitura." >&2
    exit 2
fi

step "Alvo"
# `manage.py shell` e não uma leitura do `.env` aqui: o módulo de settings vem do
# bootstrap do projeto (`config/bootstrap.py`) e reproduzir essa escolha no shell
# daria duas fontes para a mesma decisão.
uv run manage.py shell --no-imports -c '
from django.conf import settings
from django.db import connection

database = settings.DATABASES["default"]
engine = database["ENGINE"]
user = database.get("USER") or "-"
name = database["NAME"]
print(f"  settings : {settings.SETTINGS_MODULE}")
print(f"  engine   : {engine}")
print(f"  usuário  : {user}")
print(f"  banco    : {name}")
with connection.cursor():
    print(f"  conectado: {connection.vendor}")
'

step "Migrations"
if ! uv run manage.py migrate --check >/dev/null 2>&1; then
    cat >&2 <<'EOF'
Há migration pendente. O script para aqui por decisão: carregar fixture em
schema defasado falha no meio, com o banco já vazio.

Revise o SQL Oracle antes de aplicar (RUNBOOK.md §8):

    uv run manage.py showmigrations --plan | grep '\[ \]'
    uv run manage.py sqlmigrate <app> <numero>
    uv run manage.py migrate <app>
EOF
    exit 3
fi
echo "  nenhuma migration pendente"

step "Acervo atual"
report_counts

mkdir -p "$fixtures_dir"

if (( keep_fixtures )); then
    step "Fixtures 01..06 (reaproveitadas)"
    for file in "${fixture_files[@]}"; do
        if [[ ! -r "$project_root/$file" ]]; then
            echo "  $file não existe. Rode sem --keep-fixtures." >&2
            exit 2
        fi
        printf '  %s\n' "$file"
    done
else
    step "Fixtures 01..06 (exportando)"
    # Staging: um `dumpdata` que falha no meio deixaria o arquivo pela metade, e
    # o passo seguinte apaga o banco. Só entra em `docs/fixtures/` o que saiu
    # inteiro.
    staging=$(mktemp -d)
    trap 'rm -rf "$staging"' EXIT

    for index in "${!fixture_names[@]}"; do
        name="${fixture_names[$index]}"
        # shellcheck disable=SC2086  # a lista de modelos é plural de propósito
        uv run manage.py dumpdata ${fixture_models[$index]} \
            --natural-foreign --indent 2 -o "$staging/$name.json"
        printf '  %-28s %s objeto(s)\n' "$name.json" \
            "$(uv run python -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$staging/$name.json")"
    done

    uv run python scripts/normalize_fixtures.py "$staging"/*.json | sed 's|^|  |'
    mv "$staging"/*.json "$fixtures_dir/"
fi

step "Despejo integral"
uv run manage.py dumpdata "${backup_excludes[@]}" --natural-foreign --indent 2 -o "$backup_json"
gzip --keep --force "$backup_json"
printf '  %s\n' "${backup_json#"$project_root/"}" "${backup_json#"$project_root/"}.gz"

if (( export_only )); then
    step "Concluído (--export-only): nada foi apagado"
    exit 0
fi

step "Confirmação"
if (( assume_yes )); then
    echo "  --yes: seguindo sem perguntar"
else
    cat <<EOF
  O próximo passo apaga TODAS as linhas do banco impresso acima e recarrega
  apenas as fixtures 01..06. O operacional — processo, pendência, evidência,
  notificação e auditoria — não volta, exceto pelo despejo acima, à mão.
EOF
    read -r -p "  Digite APAGAR para continuar: " reply
    if [[ "$reply" != "APAGAR" ]]; then
        echo "  Cancelado. Nada foi apagado; o despejo e as fixtures ficam." >&2
        exit 4
    fi
fi

step "Esvaziando o banco"
# `flush` e não `migrate zero`: o schema fica de pé e as migrations aplicadas
# continuam registradas — `AGENTS.md` proíbe rollback para `zero` com dado real.
# No Oracle isso vira DISABLE CONSTRAINT + TRUNCATE + ENABLE, tabela por tabela,
# e no fim o sinal `post_migrate` recria contenttypes e permissões.
#
# TRUNCATE é DDL: cada tabela comita sozinha e não há rollback. Uma sessão viva
# segurando lock derruba o passo com ORA-00054 e deixa o banco esvaziado pela
# metade — é a razão de parar a aplicação antes. Se acontecer, a saída é rodar
# de novo com --keep-fixtures depois de fechar as sessões, não remendar à mão.
uv run manage.py flush --noinput
echo "  tabelas vazias, contenttypes e permissões recriadas"

step "Carregando as fixtures"
uv run manage.py loaddata "${fixture_files[@]}"

step "Sequências"
# As fixtures trazem PK explícita, e no Oracle a coluna de identidade não sabe
# disso: sem este acerto o próximo INSERT tentaria uma PK já ocupada. O bloco do
# Django só avança a sequência até passar do maior valor da tabela — nunca a
# rebobina.
uv run manage.py shell --no-imports -c '
from django.apps import apps
from django.core.management.color import no_style
from django.db import connection

models = [model for model in apps.get_models() if model._meta.managed]
statements = connection.ops.sequence_reset_sql(no_style(), models)
if statements:
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)
print(f"  {len(statements)} sequência(s) acertada(s)")
'

step "Estado final"
report_counts

step "Concluído"
cat <<EOF
  Despejo integral : ${backup_json#"$project_root/"}.gz
  Fixtures         : docs/fixtures/0{1..6}_*.json

  O que a carga não repõe, e o motivo:
  - sessão. Todo mundo precisa entrar de novo — o cookie antigo não acha sessão.
  - senha de integração. \`bind_password_ciphertext\` e \`password_ciphertext\`
    saem nulos: o texto cifrado depende do \`DJANGO_SECRET_KEY\` e no DEV a senha
    do AD e a do SMTP vêm do baseline do \`.env\` (ADR-050).
  - certificado do AD. \`certificate_file\` aponta para o storage privado; o
    arquivo continua lá, e só falta se o storage também foi refeito.
  - trilha de auditoria. Recomeça vazia, por definição.

  Confira o login e a home antes de devolver o ambiente:
      uv run manage.py check --deploy
EOF
