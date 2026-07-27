#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_root=$(cd -- "$script_dir/../.." && pwd)
env_file="$project_root/.env"
validation_sql="$script_dir/validate_senior_reference_queries.sql"
sqlcl_bin="${SGPD_SQLCL_BIN:-/opt/sqlcl/bin/sql}"

if [[ ! -r "$env_file" ]]; then
    echo "Arquivo .env não encontrado ou sem permissão de leitura." >&2
    exit 2
fi

if [[ ! -x "$sqlcl_bin" ]]; then
    echo "SQLcl não encontrado em $sqlcl_bin." >&2
    exit 2
fi

sgpd_dsn=''
sgpd_user=''
sgpd_password=''

while IFS='=' read -r env_key env_value; do
    case "$env_key" in
        SGPD_DB_NAME) sgpd_dsn="$env_value" ;;
        SGPD_DB_USER) sgpd_user="$env_value" ;;
        SGPD_DB_PASSWORD) sgpd_password="$env_value" ;;
    esac
done < "$env_file"

if [[ -z "$sgpd_dsn" || -z "$sgpd_user" || -z "$sgpd_password" ]]; then
    echo "SGPD_DB_NAME, SGPD_DB_USER e SGPD_DB_PASSWORD são obrigatórios." >&2
    exit 2
fi

if [[ ! "$sgpd_user" =~ ^[A-Za-z][A-Za-z0-9_$#]*$ ]]; then
    echo "SGPD_DB_USER possui formato não suportado para conexão segura." >&2
    exit 2
fi

sgpd_password=${sgpd_password//\"/\"\"}
sgpd_dsn=${sgpd_dsn//\"/\"\"}

printf 'set define off\nconnect %s/"%s"@"%s"\n@%s\n' \
    "$sgpd_user" \
    "$sgpd_password" \
    "$sgpd_dsn" \
    "$validation_sql" |
    "$sqlcl_bin" -s /nolog
