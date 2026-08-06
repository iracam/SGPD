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

- DEV e host de produção (ADR-055), Debian 13, Python 3.13 e Django 5.2 LTS;
- Django REST Framework, Oracle 19c e `python-oracledb` Thick;
- SPA Angular 21 standalone, PrimeNG 21 Aura e SCSS mobile first;
- sessão Django, CSRF e API na mesma origem, publicada em
  `https://sgpd.bsabioenergia.com.br` por um proxy que roda em outro host e
  termina o TLS; a aplicação sobe com `config.settings.production` (ADR-052);
- no PRD o servidor é o Gunicorn sob systemd, com **um worker** — agora por
  escolha operacional, não por trava: o cache compartilhado no Redis destravou o
  limite (ADR-057), e o boot só recusa concorrência maior se alguém devolver o
  cache ao processo. `runserver` é só de desenvolvimento. Deploy por
  `scripts/deploy.sh`, à mão, sem CI/CD (ADR-016);
- estáticos e assets da SPA saem do WhiteNoise, no próprio processo Django, em
  DEV e em PRD. Não há Nginx (ADR-014): o proxy que publica o domínio só termina
  o TLS e encaminha. Evidências nunca são servidas por servidor de arquivos;
- WhiteNoise somente para estáticos e assets da SPA;
- filesystem privado para evidências;
- Redis como requisito de runtime (ADR-057): broker do Celery e cache
  compartilhado, em container do host, compartilhado com outras aplicações — o
  projeto o consome e não o gerencia;
- worker e Beat do Celery sob systemd, executando as tarefas e a agenda;
- testes locais com Pytest e Vitest; Ruff, Mypy e build Angular;
- versões exatas em `uv.lock` e `frontend/package-lock.json`.

No DEV, a ADR-022 autoriza excepcionalmente o owner `SGPD` como conexão única
de runtime e migrations. Não criar outro usuário da aplicação. `VETORH` nunca
é usuário da aplicação e recebe somente consultas `SELECT` pelos objetos e
grants homologados.

## Regras invariantes

- `is_superuser=true` define a autoridade global do SuperAdmin ativo.
- SuperAdmin não precisa de papel `DP` nem vínculo de setor, mas continua
  sujeito a estados, validações, locks, idempotência, imutabilidade e
  auditoria. A segregação de função é a única exceção: pela ADR-048 ele decide
  a pretensão de cobrança que informou, e a auditoria registra o rompimento.
- O catálogo funcional atribuível é fixo em cinco códigos (ADR-054): `DP`,
  `DP_GERENTE`, `GRUPOS_TEMPLATE_ADMIN`, `SETORES_ADMIN` e `USUARIOS_ADMIN`.
  `DP_GERENTE` satisfaz toda exigência de `DP`; os três administrativos só
  existem em escopo global.
- Atribuir e revogar papel é ato exclusivo do SuperAdmin; `manage_roles` não é
  delegável.
- Liberar ou encerrar processo com impedimento exige
  `offboarding.override_process_blockers` no escopo e justificativa registrada.
- `RESPONSAVEL_SETOR` é capacidade derivada do vínculo vigente com o setor.
- Regras críticas vivem em services e operações compostas usam transação.
- Integrações e retries precisam ser idempotentes.
- Toda mutação relevante gera auditoria; auditoria e processos encerrados não
  são apagados. A ADR-056 abre a única exceção: o processo **não encerrado**
  pode ser excluído de vez, sob justificativa, e a trilha dele é copiada para
  `SGPD_PROCESS_PURGE` antes de sumir — muda de lugar, não desaparece.
- Snapshots e versões publicadas são imutáveis.
- Templates, perguntas e grupos são versionados; processos preservam a versão
  histórica.
- Pendências são entidades próprias. Valores são pretensões sujeitas a análise
  e a decisão explícita de `DP` vigente no escopo, que não pode ser quem
  informou o valor (ADR-048).
- Liberação é explícita e exige DP vigente no escopo ou SuperAdmin, prontidão e
  auditoria. A prontidão só é dispensada pelo override da ADR-054, com
  justificativa e trilha.
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
regras de aplicabilidade, abertura e início do processo, tarefas setoriais,
pendências estruturadas, evidências privadas, notificações por e-mail,
indicadores, relatórios com exportação auditada e sonda de operação.

`apps/reporting` é somente leitura: calcula indicador e relatório a cada
consulta, sem contador guardado, e possui uma única tabela —
`SGPD_REPORT_EXPORT`, a trilha append-only de quem exportou o quê.

Notificações usam outbox no Oracle gravado na transação do domínio, com envio
fora da requisição (ADR-049). Quem executa é o worker do Celery e quem dispara a
agenda periódica é o Beat (ADR-057): o broker carrega o sinal de trabalho, e a
fila durável continua sendo a tabela. O aviso que nasce de um ato na tela sai em
segundos, por `on_commit`; a varredura periódica é a rede de segurança. O
transporte SMTP, o remetente, o ritmo da fila e os marcos de lembrete são
configurados na central por SuperAdmin (ADR-050); o `.env` é só o baseline.

## Estado funcional resumido

A SPA cobre autenticação, contas, configuração LDAP, cascata Senior, setores,
responsáveis, configuração versionada, regras de aplicabilidade, abertura,
rascunho, início, tarefas e hub de processos. O processo nasce `RASCUNHO`,
grava snapshot e auditoria na mesma transação e impede duplicidade não
encerrada. As regras de aplicabilidade sugerem grupos pelo snapshot, mas a
seleção continua explícita: o `DP` confirma antes de salvar. O início fixa
grupos, setores, templates e perguntas, exige responsáveis vigentes e é
idempotente. Tarefas possuem controle otimista, lock, idempotência e
auditoria.

Pendências e evidências possuem a primeira fatia vertical operacional:
registro, comentários, regularização, bloqueio de conclusão, upload, hash e
download autorizado. O eixo de valor está operacional ponta a ponta — informar,
apurar, contestar e decidir, com o guard de `BLOQUEANTE_ATE_DECISAO` na
conclusão da tarefa e a consolidação por processo para conferência do `DP`.

As notificações por e-mail cobrem os marcos de prazo de `WORKFLOWS.md` §7 e os
eventos de domínio da Fase 7, com painel de falhas e reprocessamento auditado.
O painel exibe os indicadores do `DP` e do setor, os relatórios do RF-036
respondem por período — com atraso como fotografia do instante, não recorte —,
a exportação CSV é auditada e a sonda de operação torna visível o agendamento
parado (R63).
A prontidão calculada, a liberação, o processamento declarado, o encerramento,
o cancelamento e a reabertura estão operacionais pela ADR-051, com tela própria
de conferência do ciclo formal. Pela ADR-056 o cancelamento alcança também o
processo já formalizado, sob a permissão da gerência, e existe exclusão
definitiva para todo estado menos `ENCERRADO`. A caixa de notificações por usuário continua
nos incrementos seguintes.

## Leitura por escopo

| Escopo da mudança | Leitura adicional obrigatória |
| --- | --- |
| regra funcional ou aceite | `REQUIREMENTS.md` e `WORKFLOWS.md` |
| backend, API ou módulo | seções afetadas de `ARCHITECTURE.md` |
| model, migration ou SQL SGPD | `DATA_MODEL.md` e ADRs relacionadas |
| Senior/Oracle cadastral | `INTEGRATION_SENIOR_ORACLE.md` |
| autenticação, autorização, upload ou LGPD | `SECURITY.md` e integração aplicável |
| papel funcional, atribuição ou override de impedimento | ADR-054 e `SECURITY.md` §3–§4 |
| exclusão de processo, cancelamento ou retenção | ADR-056, RF-038 e `SECURITY.md` §14 |
| Angular, layout ou entrega SPA | `ARCHITECTURE.md` e ADRs 025–028 |
| notificação, fila ou agendamento | ADR-049, ADR-057, `WORKFLOWS.md` §7 e `ENVIRONMENT.md` §3 |
| indicador, relatório ou exportação | `REQUIREMENTS.md` RF-034 a RF-036 e `SECURITY.md` §5–§6 |
| operação, monitoramento ou plantão | `RUNBOOK.md` e `ENVIRONMENT.md` §7 |
| settings, transporte, proxy ou publicação | `SECURITY.md` §10, ADR-052 e `RUNBOOK.md` §7 |
| deploy, servidor de aplicação ou go-live | ADR-055, `RUNBOOK.md` §11 e `ENVIRONMENT.md` §4 |
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
uv run manage.py check --deploy
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
