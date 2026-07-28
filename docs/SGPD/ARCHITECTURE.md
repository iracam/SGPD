# Arquitetura

## 1. Visão geral

```text
Usuário DEV
    |
    v
SPA Angular 21 + PrimeNG (mobile first)
    |
    |  mesma origem; sessão Django com CSRF
    v
Django 5.2
    |
    +--> view catch-all (index.html da SPA)
    |
    +--> WhiteNoise (arquivos estáticos e assets da SPA)
    |
    +--> API /api/v1/ (auth, accounts, references)
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

A interface server-side anterior permanece em operação até a conclusão da Fase
G da migração descrita em `MIGRATION_FRONTEND_SPA.md`. Ela não recebe telas
novas.

## 2. Componentes

### Backend

- Python 3.13;
- Django 5.2 LTS;
- Django REST Framework 3.17;
- DRF como única superfície funcional da aplicação, em `/api/v1/`;
- WhiteNoise para arquivos estáticos e para os assets da SPA;
- view Django dedicada para servir o `index.html` da SPA.

WhiteNoise não será usado para servir evidências ou outros uploads de usuários.

### Frontend

- Angular 21, standalone, sem NgModules;
- estado por signals, sem biblioteca de gerência de estado;
- PrimeNG 21 com preset Aura e primeicons;
- SCSS mobile first, com pontos de quebra centralizados em tokens;
- roteamento em dois níveis, com carregamento sob demanda por rota;
- Vitest para testes.

Nenhum código é carregado de CDN: componentes, ícones e fontes são empacotados
no build. A restrição de não depender de rede externa no navegador, estabelecida
originalmente para o HTMX, permanece válida.

A SPA não implementa regra de negócio. Ela consome a API, exibe estado e aplica
a autorização recebida do servidor apenas para orientar a navegação; a decisão
de autorização continua sendo do backend.

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
- a SPA autentica por sessão Django com proteção CSRF em origem única,
  conforme a ADR-026; não há JWT nem credencial em armazenamento local;
- a administração de contas usa services transacionais, expostos por
  `/api/v1/accounts/` e consumidos pela SPA;
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

frontend/
└── src/app/
    ├── core/       auth, config, layout, theme
    └── features/   uma pasta por tela
```

Novos módulos serão criados somente quando o respectivo checkpoint exigir.
`accounts` contém conta local, papéis, escopos, services, autorização, API,
vínculo administrativo com o AD e auditoria de contas. `core` contém os
endpoints operacionais e a view que serve a SPA. `integrations/senior` contém
SQL, DTOs e o repository somente leitura. Não existem models para objetos do
Senior.

A estrutura de `frontend/` está detalhada em `MIGRATION_FRONTEND_SPA.md` §5.

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

Interface cadastral server-side substituída na SPA pela Fase F e mantida
temporariamente até a remoção da Fase G:

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

A SPA consome os mesmos quatro endpoints na rota `/fe/colaboradores`, cancela
consultas obsoletas ao trocar um nível, limita a busca remota a 100 caracteres
e 20 colaboradores e não projeta CPF ou cria snapshot.

Endpoints de autenticação e contexto implementados para a SPA:

```text
GET  /api/v1/auth/csrf/
POST /api/v1/auth/login/
POST /api/v1/auth/logout/
GET  /api/v1/auth/me/
GET  /api/v1/auth/context/
POST /api/v1/auth/change-password/
```

`GET /api/v1/auth/context/` devolve papéis, permissões efetivas e escopos de
empresa e filial do usuário autenticado. Ele orienta a navegação da SPA e
substitui o context processor da interface server-side; a decisão de
autorização continua sendo aplicada em cada endpoint e em cada service.

Endpoints de contas implementados:

```text
GET  POST   /api/v1/accounts/users/
GET  PATCH  /api/v1/accounts/users/{id}/
POST        /api/v1/accounts/users/{id}/reset-password/
POST        /api/v1/accounts/users/{id}/roles/
POST        /api/v1/accounts/users/{id}/ad-link/
POST        /api/v1/accounts/users/{id}/ad-unlink/
POST        /api/v1/accounts/role-assignments/{id}/revoke/
GET  POST   /api/v1/accounts/roles/
GET  PATCH  /api/v1/accounts/roles/{id}/
GET         /api/v1/accounts/permissions/
GET         /api/v1/accounts/audit/
```

Cada endpoint valida entrada, invoca o service correspondente e traduz o
resultado. Nenhum implementa regra de negócio.

A autorização é declarada por endpoint e reavaliada a cada requisição:
`manage_users` para usuários e senha, `manage_roles` para papéis, atribuições e
o catálogo de permissões, `link_ad_identity` para o vínculo com o AD e
`view_account_audit` para a auditoria. O service revalida a mesma permissão no
próprio limite, conforme a ADR-024, de modo que a checagem do endpoint é
redundante por decisão e não é o único guarda.

As listagens usam paginação por `offset` e `limit`, com padrão de 50 e teto de
200, sem `COUNT(*)`. A auditoria aceita filtro por `target_user` e
`event_type`.

Toda resposta de erro da API usa o envelope `{code, message, details}`. O
`ValidationError` levantado pelos services é traduzido em `400` com erros por
campo, por um handler único do DRF. Os endpoints cadastrais do Senior, criados
na Fase 2 com `{detail}`, foram alinhados ao mesmo envelope.

Códigos em uso:

| Código | HTTP | Situação |
| --- | --- | --- |
| `validation_error` | 400 | entrada inválida, com `details` por campo |
| `not_authenticated` | 401 | sem sessão |
| `invalid_credentials` | 401 | usuário ou senha incorretos, ou conta inativa |
| `permission_denied` | 403 | autenticado, fora do escopo ou sem permissão |
| `password_change_required` | 403 | senha temporária pendente de troca |
| `not_found` | 404 | recurso inexistente |
| `method_not_allowed` | 405 | verbo não suportado |
| `throttled` | 429 | excesso de tentativas de login |
| `senior_unavailable` | 503 | Senior HCM indisponível |
| `senior_contract_error` | 502 | resposta inválida da fonte cadastral |

Requisição sem sessão recebe `401`, e não o `403` que o DRF produziria por
`SessionAuthentication` não publicar cabeçalho `WWW-Authenticate`. A distinção
permite à SPA rotear para o login em vez de exibir erro, e separa "autentique-se"
de "você não pode".

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

Com a ADR-025, a API passa a ser a única superfície funcional da aplicação. A
afirmação anterior de que a UI server-side poderia usar services diretamente
vale apenas para as telas ainda não migradas e para os comandos de gestão.

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
- WhiteNoise para arquivos estáticos e para os assets da SPA;
- SPA construída por `ng build` e servida pelo próprio Django, em origem única;
- durante o desenvolvimento, `ng serve` com proxy para o Django;
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
- teste de permissão negada para cada endpoint da API;
- testes de frontend com Vitest, cobrindo guarda, interceptador, serviço de
  autenticação e filtragem do menu por permissão;
- conferência visual em todos os pontos de quebra ao encerrar cada fase de
  interface, começando pelo menor;
- testes end-to-end dos fluxos críticos.
