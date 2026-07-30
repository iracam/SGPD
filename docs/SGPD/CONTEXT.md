# Contexto Operacional do SGPD

## Finalidade

Este é o contexto mínimo vigente para iniciar qualquer tarefa. Ele não substitui
requisitos, ADRs ou documentos especializados. O estado e o próximo incremento
estão em `CHECKPOINT.md`; decisões são localizadas por `DECISIONS_INDEX.md`.

## Produto e fronteiras

O SGPD / DesligaFlow orquestra o processo demissional entre DP e setores:
abertura, snapshot, tarefas, checklists, pendências, evidências, valores em
análise, prontidão, liberação e auditoria. O Senior HCM continua sendo a fonte
oficial do vínculo e da rescisão.

O SGPD não calcula rescisão, não aplica descontos, não movimenta o vínculo e
não escreve em tabelas internas do Senior. Referências cadastrais são lidas
online pelo contrato SQL homologado e o snapshot histórico é criado na abertura.

## Stack e ambiente vigentes

- DEV único, Debian 13, Python 3.13 e Django 5.2 LTS;
- Django REST Framework, Oracle 19c e `python-oracledb` Thick;
- SPA Angular 21 standalone, PrimeNG 21 Aura e SCSS mobile first;
- sessão Django, CSRF e API na mesma origem;
- WhiteNoise somente para estáticos e assets da SPA;
- filesystem privado para evidências;
- Redis e worker somente quando uma funcionalidade exigir;
- testes locais com Pytest e Vitest; Ruff, Mypy e build Angular;
- versões exatas em `uv.lock` e `frontend/package-lock.json`.

No DEV, a ADR-022 autoriza excepcionalmente o owner `SGPD` como conexão única
de runtime e migrations. Não criar outro usuário da aplicação. `VETORH` nunca
é usuário da aplicação e recebe somente consultas `SELECT` pelos objetos e
grants homologados.

## Regras invariantes

- `is_superuser=true` define a autoridade global do SuperAdmin ativo.
- SuperAdmin não precisa de papel `DP` nem vínculo de setor, mas continua
  sujeito a estados, validações, segregação, locks, idempotência, imutabilidade
  e auditoria.
- `DP` é o único papel funcional atribuível.
- `RESPONSAVEL_SETOR` é capacidade derivada do vínculo vigente com o setor.
- Regras críticas vivem em services e operações compostas usam transação.
- Integrações e retries precisam ser idempotentes.
- Toda mutação relevante gera auditoria; auditoria e processos encerrados não
  são apagados.
- Snapshots e versões publicadas são imutáveis.
- Templates, perguntas e grupos são versionados; processos preservam a versão
  histórica.
- Pendências são entidades próprias. Valores são pretensões sujeitas a análise
  e aprovação segregada.
- Liberação é explícita e exige DP vigente no escopo ou SuperAdmin, prontidão e
  auditoria.
- A SPA não implementa regras de negócio nem constitui barreira de autorização.
- Frontend é mobile first; não usar consultas CSS `max-width`.

## Arquitetura em uma página

O backend é API-only, exceto pelo Django Admin técnico. Casos de uso ficam em
`apps/*/services.py`, APIs validam o contrato e delegam ao domínio. O Oracle
armazena dados do SGPD e metadados; evidências ficam fora dele. Consultas ao
Senior usam repository SQL explícito, parametrizado, sem models e sem tabelas
`REF_*`.

Módulos já ativos: contas e autorização, auditoria, integração Senior,
configuração LDAP/AD, setores e responsáveis, templates e grupos versionados,
abertura e início do processo, tarefas setoriais, pendências estruturadas,
evidências privadas e painéis iniciais.

## Estado funcional resumido

A SPA cobre autenticação, contas, configuração LDAP, cascata Senior, setores,
responsáveis, configuração versionada, abertura, rascunho, início, tarefas e
hub de processos. O processo nasce `RASCUNHO`, grava snapshot e auditoria na
mesma transação e impede duplicidade não encerrada. O início fixa grupos,
setores, templates e perguntas, exige responsáveis vigentes e é idempotente.
Tarefas possuem controle otimista, lock, idempotência e auditoria.

Pendências e evidências possuem a primeira fatia vertical operacional:
registro, comentários, regularização, bloqueio de conclusão, upload, hash e
download autorizado. Valores, notificações, prontidão, liberação, encerramento
formal e relatórios ainda pertencem aos incrementos seguintes.

## Leitura por escopo

| Escopo da mudança | Leitura adicional obrigatória |
| --- | --- |
| regra funcional ou aceite | `REQUIREMENTS.md` e `WORKFLOWS.md` |
| backend, API ou módulo | seções afetadas de `ARCHITECTURE.md` |
| model, migration ou SQL SGPD | `DATA_MODEL.md` e ADRs relacionadas |
| Senior/Oracle cadastral | `INTEGRATION_SENIOR_ORACLE.md` |
| autenticação, autorização, upload ou LGPD | `SECURITY.md` e integração aplicável |
| Angular, layout ou entrega SPA | `ARCHITECTURE.md` e ADRs 025–028 |
| direção de produto | `VISION.md` |
| planejamento futuro | `ROADMAP.md` |

Para decisões, consulte primeiro `DECISIONS_INDEX.md` e depois leia
integralmente as ADRs relacionadas em `DECISIONS.md`. Histórico de execução só
é necessário para investigação, regressão ou rastreabilidade.

## Validação padrão

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy apps config tests manage.py
uv run manage.py check
uv run manage.py makemigrations --check --dry-run --settings=config.settings.test
npm --prefix frontend test
npm --prefix frontend run build
```

Antes de aplicar migration: revisar o SQL Oracle, locks, índices, volume,
rollback e compatibilidade. Consultas ou smokes no Senior permanecem somente
leitura.

## Manutenção documental

Cada fato deve ter uma fonte canônica. Atualize:

- `CHECKPOINT.md` somente quando estado, bloqueio ou próximo incremento mudar;
- o documento especializado quando o contrato correspondente mudar;
- `DECISIONS.md` somente para decisão arquitetural relevante;
- `history/checkpoints/` com registro conciso de entrega, sem repetir o mesmo
  relato nos demais documentos.
