# Arquitetura

## 1. Visão geral

```text
Usuário corporativo
        |
        v
Nginx / Reverse Proxy
        |
        v
Django + HTMX + Alpine
        |
        +-----------------------+
        |                       |
        v                       v
Oracle SGPD                 Redis
        |                       |
        v                       v
Views / Integração          Worker assíncrono
Senior HCM                  E-mail / sincronização
```

## 2. Componentes

### Aplicação web

- Django;
- templates server-side;
- HTMX para interações parciais;
- Alpine.js para comportamento local;
- Tailwind/daisyUI para layout;
- DRF para APIs internas e futuras integrações.

### Banco

- Oracle;
- schema próprio;
- migrations controladas;
- sequences ou identity conforme padrão homologado;
- timezone e encoding definidos no início.

### Processamento assíncrono

Usar Celery ou Django-Q2 para:

- envio de e-mails;
- sincronização com Senior;
- escaladas;
- lembretes;
- geração de relatórios;
- reprocessamentos.

### Cache e filas

Redis para:

- broker;
- cache;
- locks distribuídos;
- controle de idempotência;
- limitação de tarefas.

### Autenticação

Opções:

1. LDAP/Active Directory direto;
2. autenticação corporativa central;
3. Keycloak em fase posterior.

MVP recomendado: LDAP/AD direto, com grupos mapeados para papéis.

### Arquivos

Opções:

- filesystem corporativo;
- storage S3 compatível;
- object storage interno;
- banco apenas para metadados.

Recomendação: storage externo ao Oracle, com hash SHA-256 no banco.

## 3. Aplicações Django

Estrutura sugerida:

```text
apps/
├── accounts/
├── core/
├── references/
├── sectors/
├── templates_engine/
├── offboarding/
├── pending_items/
├── evidence/
├── approvals/
├── notifications/
├── integrations/
├── audit/
└── reporting/
```

## 4. Serviços de domínio

Regras críticas devem ficar fora de views e signals genéricos.

Serviços sugeridos:

- `OpenOffboardingProcessService`
- `ResolveValidationGroupsService`
- `GenerateSectorTasksService`
- `CreateEmployeeSnapshotService`
- `RegisterPendingItemService`
- `EvaluateProcessReadinessService`
- `ReleaseForTerminationService`
- `CloseOffboardingProcessService`
- `SyncSeniorReferencesService`
- `EscalateOverdueTasksService`

## 5. Eventos de domínio

Eventos sugeridos:

- `ProcessOpened`
- `ProcessStarted`
- `SectorTaskCreated`
- `SectorTaskCompleted`
- `PendingItemCreated`
- `PendingItemResolved`
- `ChargeRequested`
- `ChargeApproved`
- `ProcessReadyForHR`
- `ProcessReleased`
- `TerminationRegistered`
- `ProcessClosed`

Eventos devem ser usados para desacoplar notificações e integrações.

## 6. API

Endpoints iniciais sugeridos:

```text
GET  /api/v1/references/companies/
GET  /api/v1/references/branches/?company=
GET  /api/v1/references/employee-types/?company=&branch=
GET  /api/v1/references/employees/?company=&branch=&type=&q=

POST /api/v1/processes/
GET  /api/v1/processes/
GET  /api/v1/processes/{uuid}/
POST /api/v1/processes/{uuid}/start/
POST /api/v1/processes/{uuid}/release/
POST /api/v1/processes/{uuid}/cancel/

GET  /api/v1/tasks/
POST /api/v1/tasks/{id}/start/
POST /api/v1/tasks/{id}/complete/

POST /api/v1/pending-items/
POST /api/v1/pending-items/{uuid}/resolve/
POST /api/v1/pending-items/{uuid}/decision/

POST /api/v1/evidence/
```

A UI server-side pode usar services diretamente. API não precisa ser a única camada.

## 7. Observabilidade

- logs JSON;
- correlation ID;
- métricas de tarefas;
- monitoramento de filas;
- health checks;
- registro de falhas de integração;
- alertas para e-mails falhos;
- painel de sincronização.

## 8. Ambientes

- desenvolvimento;
- homologação;
- produção.

Cada ambiente deverá ter:

- schema próprio;
- credenciais próprias;
- storage próprio;
- SMTP controlado;
- variáveis de ambiente;
- logs separados.

## 9. Implantação

Sugestão:

- Docker Compose para DEV/HML;
- Gunicorn;
- Nginx;
- Redis;
- worker Celery;
- scheduler Celery Beat;
- Oracle externo;
- armazenamento de evidências externo;
- systemd ou plataforma de containers em produção.

## 10. Testes

- unitários para regras;
- integração para Oracle;
- testes de services;
- testes de autorização;
- testes de workflow;
- testes de sincronização;
- testes end-to-end dos fluxos críticos.
