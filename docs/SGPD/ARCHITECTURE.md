# Arquitetura

## 1. Visão geral

```text
Usuário DEV
    |
    v
Django + HTMX + Alpine
    |
    +--> WhiteNoise (arquivos estáticos)
    |
    +--> Oracle SGPD --> Views / Integração Senior HCM
    |
    +--> Redis em container, quando necessário
             |
             v
        Worker assíncrono
```

## 2. Componentes

### Aplicação web

- Django;
- templates server-side;
- HTMX para interações parciais;
- Alpine.js para comportamento local;
- Tailwind/daisyUI para layout;
- WhiteNoise para arquivos estáticos;
- DRF para APIs internas e futuras integrações.

WhiteNoise não será usado para servir evidências ou outros uploads de usuários.

### Banco

- Oracle Database 19c;
- Oracle Instant Client 19.28 disponível no DEV;
- schema próprio;
- migrations controladas;
- sequences ou identity conforme padrão homologado;
- timezone e encoding definidos no início.

### Processamento assíncrono

Quando o processamento assíncrono se tornar necessário, usar Celery ou Django-Q2 para:

- envio de e-mails;
- sincronização com Senior;
- escaladas;
- lembretes;
- geração de relatórios;
- reprocessamentos.

### Cache e filas

Redis será iniciado em container somente quando houver funcionalidade que dependa dele. Seus usos previstos são:

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

No DEV, evidências serão armazenadas no filesystem local privado:

- caminho configurável por `EVIDENCE_STORAGE_PATH`;
- padrão inicial `media/evidence`;
- metadados e hash SHA-256 mantidos no Oracle;
- acesso somente por views autorizadas da aplicação;
- diretório fora dos arquivos estáticos e não servido pelo WhiteNoise;
- permissões do sistema operacional restritas ao usuário da aplicação.

Backup, retenção e antivírus ainda deverão ser definidos antes do uso com dados reais.

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

O escopo atual possui somente o ambiente DEV.

HML e PRD não fazem parte da estrutura atual. Caso sejam criados futuramente, deverão ser tratados por nova decisão arquitetural, com credenciais, schema, storage e logs separados.

## 9. Execução no DEV

- servidor Django no ambiente DEV;
- WhiteNoise para arquivos estáticos;
- sem Nginx ou reverse proxy no escopo atual;
- sem pipeline de CI/CD;
- Oracle externo;
- Redis em container somente quando necessário;
- worker e scheduler somente quando houver casos de uso assíncronos;
- armazenamento de evidências separado dos arquivos estáticos.

## 10. Testes

- unitários para regras;
- integração para Oracle;
- testes de services;
- testes de autorização;
- testes de workflow;
- testes de sincronização;
- testes end-to-end dos fluxos críticos.
