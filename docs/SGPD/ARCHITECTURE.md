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
    +--> Oracle 19c
           |
           +--> Schema SGPD (dados operacionais)
           |
           +--> VETORH (SELECT direto em objetos autorizados)
    |
    +--> Redis em container, quando necessário
             |
             v
        Worker assíncrono
```

## 2. Componentes

### Aplicação web

- Python 3.13;
- Django 5.2 LTS;
- Django REST Framework 3.17;
- templates server-side;
- HTMX para interações parciais;
- Alpine.js para comportamento local;
- Tailwind/daisyUI para layout;
- WhiteNoise para arquivos estáticos;
- DRF para APIs internas e futuras integrações.

WhiteNoise não será usado para servir evidências ou outros uploads de usuários.
O runtime HTMX 2.0.10 é versionado em `static/vendor/htmx/` e servido
localmente pelo mesmo pipeline de arquivos estáticos, sem CDN ou dependência de
rede no navegador.

### Banco

- Oracle Database 19c;
- Oracle Instant Client 19.28 disponível no DEV;
- `python-oracledb` em modo Thick, necessário porque a credencial `SGPD`
  possui verificador de senha não suportado pelo modo Thin;
- schema próprio;
- migrations controladas;
- sequences ou identity conforme padrão homologado;
- timezone e encoding definidos no início.

### Processamento assíncrono

Quando o processamento assíncrono se tornar necessário, usar Celery ou Django-Q2 para:

- envio de e-mails;
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

O cadastro funcional de usuários pertence ao SGPD:

- usuários, gestores, e-mails, papéis e escopos são mantidos no schema SGPD;
- o Senior HCM não provisiona usuários;
- o MVP usa autenticação local;
- a administração de contas usa services transacionais e interface
  server-side em `/accounts/`;
- os services administrativos repetem a autorização no limite do caso de uso,
  independentemente da proteção aplicada pelas views;
- papéis possuem permissões delegáveis e atribuições com escopo global, por
  empresa ou por filial, validade e revogação lógica;
- senha temporária pode exigir troca no primeiro acesso;
- login, logout, falha de autenticação e toda manutenção de conta são
  auditados com correlation ID;
- eventos de auditoria rejeitam alteração e exclusão tanto por instância quanto
  por operações em lote do ORM;
- o vínculo administrativo com o Active Directory adiciona identificador
  externo opaco e único à conta existente, após confirmação humana;
- após a vinculação, o AD será o provedor de autenticação e o SGPD continuará como fonte de perfis e autorizações.

O vínculo com AD não usa e-mail como chave, impede associação duplicada e não
ativa autenticação LDAP. Endpoint, TLS, base de busca, atributo identificador e
backend de autenticação ainda dependem de homologação com a Infraestrutura.

### Arquivos

No DEV, evidências serão armazenadas no filesystem local privado:

- caminho configurável por `EVIDENCE_STORAGE_PATH`;
- padrão inicial `media/evidence`;
- metadados e hash SHA-256 mantidos no Oracle;
- acesso somente por views autorizadas da aplicação;
- diretório fora dos arquivos estáticos e não servido pelo WhiteNoise.

## 3. Aplicações Django

Estrutura incremental adotada:

```text
apps/
├── accounts/
├── core/
└── integrations/
    └── senior/
```

Novos módulos serão criados somente quando o respectivo checkpoint exigir.
`accounts` contém conta local, papéis, escopos, services, autorização,
manutenção server-side, vínculo administrativo com o AD e auditoria de contas.
`core` contém os endpoints operacionais. `integrations/senior` contém SQL,
DTOs e o repository somente leitura. Não existem models para objetos do
Senior.

## 4. Serviços de domínio

Regras críticas devem ficar fora de views e signals genéricos.

Serviços sugeridos:

- `CreateUserService`
- `UpdateUserService`
- `ResetPasswordService`
- `CreateRoleService`
- `UpdateRoleService`
- `AssignRoleService`
- `RevokeRoleService`
- `LinkAdIdentityService`
- `UnlinkAdIdentityService`
- `OpenOffboardingProcessService`
- `ResolveValidationGroupsService`
- `GenerateSectorTasksService`
- `CreateEmployeeSnapshotService`
- `RegisterPendingItemService`
- `EvaluateProcessReadinessService`
- `ReleaseForTerminationService`
- `CloseOffboardingProcessService`
- `QuerySeniorEmployeesService`
- `EscalateOverdueTasksService`

### Consulta ao Senior

- views Django e endpoints chamam um service/repository de consulta;
- o repository usa cursor Oracle e SQL `SELECT` parametrizado;
- não existem models Django, models não gerenciados ou tabelas `REF_*` para objetos do Senior;
- a conexão de runtime do SGPD recebe grants explícitos apenas nos objetos `VETORH` homologados;
- SQL não fica espalhado em templates, serializers ou views de apresentação;
- a abertura do processo copia o resultado autorizado para o snapshot histórico do SGPD.

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

Endpoints cadastrais implementados:

```text
GET  /api/v1/references/companies/
GET  /api/v1/references/branches/?company=
GET  /api/v1/references/employee-types/?company=&branch=
GET  /api/v1/references/employees/?company=&branch=&employee_type=&q=
```

Todos exigem usuário autenticado, permissão `query_senior_references` e escopo
compatível com empresa/filial. A listagem de colaboradores não retorna CPF,
usa limite padrão de 20 e máximo absoluto de 100. A paginação por offset não
executa `COUNT(*)`.

Interface cadastral implementada:

```text
GET /references/senior/
GET /references/senior/branches/?company=
GET /references/senior/employee-types/?company=&branch=
GET /references/senior/employees/?company=&branch=&employee_type=&q=
```

A página e os fragmentos HTMX reutilizam o repository somente leitura e a
autorização por escopo. Cada troca de nível remove as escolhas descendentes; a
busca de colaboradores retorna no máximo 20 opções e não exibe CPF. Respostas
de erro preservam os estados HTTP `400`, `403`, `502` e `503` e são exibidas no
alvo parcial sem detalhes do Oracle.

Endpoints de domínio planejados:

```text
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

- logs JSON configurados na saída padrão;
- correlation ID aceito em `X-Correlation-ID` ou gerado pela aplicação e
  devolvido na resposta;
- métricas de tarefas;
- monitoramento de filas;
- health checks separados em liveness e readiness;
- registro de falhas de integração;
- alertas para e-mails falhos;
- métricas de latência, timeout e indisponibilidade das consultas ao Senior.

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

- SQLite em memória para testes unitários da fundação;
- unitários para regras;
- integração para Oracle;
- testes de services;
- testes de autorização;
- testes de workflow;
- testes de contrato e integração das consultas somente leitura ao Senior;
- testes end-to-end dos fluxos críticos.
