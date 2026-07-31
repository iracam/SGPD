# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é

SGPD / DesligaFlow: sistema corporativo que orquestra o processo demissional entre DP e setores (abertura, snapshot, tarefas, checklists, pendências, evidências, liberação, auditoria). O Senior HCM permanece a fonte oficial do vínculo e da rescisão — o SGPD nunca escreve em tabelas do Senior, nunca calcula rescisão, nunca aplica descontos.

## Leitura obrigatória antes de implementar

Ordem definida em `AGENTS.md` §2 — siga-a:

1. `docs/SGPD/CONTEXT.md` — contexto vigente e **matriz de leitura por escopo** (diz qual doc adicional ler para cada tipo de mudança);
2. `docs/SGPD/CHECKPOINT.md` — estado atual e próximo incremento;
3. `docs/SGPD/DECISIONS_INDEX.md` → ADRs completas em `DECISIONS.md`.

`AGENTS.md` contém as proibições, regras de domínio e Definition of Done — todas valem aqui. `docs/SGPD/history/` só é leitura para investigação/regressão.

## Comandos

```bash
# Backend (uv gerencia o venv; nunca pip)
uv sync --dev
uv run pytest                          # suíte toda
uv run pytest tests/test_offboarding.py -k nome_do_teste   # um teste
uv run ruff check .
uv run ruff format --check .
uv run mypy apps config tests manage.py
uv run manage.py check
uv run manage.py makemigrations --check --dry-run --settings=config.settings.test

# Frontend (sempre npm ci, nunca npm install)
npm --prefix frontend ci
npm --prefix frontend test             # Vitest via ng test
npm --prefix frontend run build

# Execução local: Django serve a SPA construída em :8000
uv run manage.py runserver
# Dev do frontend: ng serve em :4200 com proxy de /api e /admin para :8000
npm --prefix frontend start
```

Testes usam `config.settings.test` (SQLite, sem Oracle). Pytest só coleta `tests/` na raiz.

## Arquitetura

**Backend API-only** (Django 5.2 + DRF, Python 3.13, Oracle 19c via `python-oracledb` Thick). A SPA Angular é a única interface (ADR-025); o Django Admin somente leitura é ferramenta técnica. API publicada em `/api/v1/`; sessão Django + CSRF na mesma origem (ADR-026) — sem tokens.

- **Regras críticas vivem em `apps/*/services.py`** (`service.execute(command)`); views/serializers só validam contrato e delegam. Nada de regra em signals, templates ou no cliente Angular.
- Operações compostas usam `transaction.atomic()`; pontos críticos usam versão otimista/lock + `Idempotency-Key`; toda mutação relevante gera auditoria append-only.
- **Integração Senior**: repository SQL explícito e parametrizado, somente `SELECT`, sem models Django e sem tabelas `REF_*` espelho. Snapshot do colaborador é copiado na abertura do processo e é imutável.
- Apps ativos: `accounts` (auth local + AD via django-auth-ldap, papéis, auditoria de contas), `core`, `sectors`, `templates_engine` (templates/grupos/perguntas versionados, publicação imutável), `offboarding` (processo, tarefas), `pending_items`, `evidence` (filesystem privado, SHA-256, download autorizado), `integrations` (Senior), `system_settings` (config LDAP/AD).
- **Frontend**: Angular 21 standalone, signals, PrimeNG 21 Aura, SCSS **mobile first — proibido `max-width` em media queries** (ADR-028). `src/app/core/` (auth, config, layout, theme), `src/app/features/` (uma pasta por tela), rotas sob `/fe/`. Sem CDN: tudo empacotado no build.

**Autorização**: `DP` é o único papel atribuível; `RESPONSAVEL_SETOR` é derivado do vínculo vigente com o setor. SuperAdmin (`is_superuser=true`) tem autoridade global de autorização (ADR-044) mas continua sujeito a estados, validações, locks, idempotência e auditoria.

**Oracle DEV**: owner `SGPD` é a conexão única (ADR-022); `VETORH` recebe apenas `SELECT`. Migrations exigem revisão do SQL Oracle antes de aplicar; nunca rollback para `zero` com dados reais. O ambiente é DEV único, sem CI/CD — validação é sempre local.

## Ao concluir

Rodar a validação padrão (bloco de comandos acima), atualizar `docs/SGPD/CHECKPOINT.md` quando estado/bloqueio/próximo incremento mudar, e registrar ADR em `DECISIONS.md` apenas para decisão arquitetural relevante. Cada fato tem uma fonte canônica — não repetir o mesmo relato em vários docs.
