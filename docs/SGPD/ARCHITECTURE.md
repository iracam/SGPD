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

O Django Admin, somente leitura, é a única interface Django que renderiza
templates.

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
no build. O navegador não depende de rede externa para carregar a interface.

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

Implementado pela ADR-049, sem broker: a fila de notificações é a tabela
`SGPD_NOTIFICATION`, gravada na mesma transação do fato que a origina, e o
envio acontece fora da requisição por dois comandos acionados pelo agendador do
sistema operacional:

- `manage.py sgpd_scan_notifications` varre prazos e enfileira lembretes,
  atrasos e escaladas;
- `manage.py sgpd_dispatch_notifications` envia o que está na fila, registra
  cada tentativa em `SGPD_NOTIFICATION_ATTEMPT` e reabre o que ficou preso.

Ambos são idempotentes: a chave de deduplicação impede o aviso repetido e o
lock impede o envio concorrente. A entrega é ao menos uma vez.

O transporte é dinâmico: `EMAIL_BACKEND` é `ConfiguredEmailBackend`, que lê o
singleton `SGPD_EMAIL_CONFIG` a cada envio (ADR-050). Mudar servidor, remetente,
ritmo da fila ou marcos de lembrete não exige reinício, e o interruptor de envio
segura a fila sem perder mensagem.

Relatórios e reprocessamentos em massa continuam sem caso de uso assíncrono.

### Cache e filas

Redis continua sem caso de uso (ADR-015 e ADR-049) e não faz parte do runtime.
Se cache, lock distribuído ou limitação de taxa aparecerem, ele sobe em
container conforme a ADR-015.

### Autenticação

O cadastro funcional de usuários pertence ao SGPD:

- usuários, e-mails, papéis funcionais e escopos são mantidos no schema SGPD;
- o Senior HCM não provisiona usuários;
- a autenticação local permanece disponível enquanto a integração AD estiver
  desabilitada e para a contingência administrativa controlada;
- a SPA autentica por sessão Django com proteção CSRF em origem única,
  conforme a ADR-026; não há JWT nem credencial em armazenamento local;
- a administração de contas usa services transacionais, expostos por
  `/api/v1/accounts/` e consumidos pela SPA;
- os services administrativos repetem a autorização no limite do caso de uso,
  independentemente da proteção aplicada pelos endpoints;
- o catálogo de papéis atribuíveis é fixo em `DP`; `RESPONSAVEL_SETOR` é
  derivado do vínculo vigente com o setor e herda o escopo organizacional
  desse setor;
- SuperAdmin é a autoridade global explícita por `is_superuser`, fora do
  catálogo funcional; acessa todos os processos, tarefas, menus e casos de uso
  sem receber atribuições artificiais;
- senha temporária pode exigir troca no primeiro acesso;
- login, logout, falha de autenticação e toda manutenção de conta são
  auditados com correlation ID;
- eventos de auditoria rejeitam alteração e exclusão tanto por instância quanto
  por operações em lote do ORM;
- `LDAP_ENABLED` habilita descoberta administrativa de grupos e usuários,
  importação explícita e vínculo verificado;
- `LDAP_AUTHENTICATION_ENABLED` habilita separadamente o backend
  `django-auth-ldap`, sem provisionamento implícito no login;
- a identidade é resolvida pelo `objectGUID` estável, convertido para UUID
  canônico; e-mail e login não são chaves de vínculo;
- uma conta SGPD pode ser cadastrada localmente e vinculada depois, ou criada
  explicitamente a partir de uma identidade pesquisada no AD;
- contas comuns vinculadas deixam de aceitar senha local quando a autenticação
  AD está ativa; somente a contingência de superusuário configurada permanece;
- grupos AD restringem pesquisa e elegibilidade, mas nunca criam papéis,
  permissões ou escopos no SGPD.
- a configuração LDAP efetiva usa o singleton versionado
  `SGPD_LDAP_CONFIG`, com o `.env` como baseline de primeiro boot;
- `/api/v1/settings/ldap/` e a SPA em
  `/fe/configuracoes/autenticacao` são exclusivas de `is_superuser`, sem
  permissão funcional delegável;
- a senha de bind persistida é cifrada com Fernet a partir do
  `DJANGO_SECRET_KEY` e nunca é projetada; a rotação dessa chave exige
  regravação coordenada do segredo;
- certificados enviados ficam no storage privado
  `SYSTEM_CONFIGURATION_STORAGE_PATH`, fora do WhiteNoise, e são normalizados
  para PEM com hash e metadados no Oracle;
- o backend LDAP monta sua configuração a cada autenticação, de forma que uma
  alteração validada entra em vigor sem mutar settings globais ou reiniciar o
  processo.

O backend, os filtros, as APIs e a interface estão implementados conforme a
ADR-029 e a simplificação de transporte da ADR-032. Descoberta, busca,
importação, vínculo e login usam a mesma escolha do SuperAdmin. Com TLS, a
aplicação monta LDAPS e valida a CA; sem TLS, LDAP simples continua funcional
com warning permanente sobre credenciais e senhas sem criptografia. Bind,
bases e grupo estão homologados. O contrato completo está em
`INTEGRATION_ACTIVE_DIRECTORY.md`.

### Arquivos

No DEV, evidências serão armazenadas no filesystem local privado:

- caminho configurável por `EVIDENCE_STORAGE_PATH`;
- padrão inicial `media/evidence`;
- metadados e hash SHA-256 mantidos no Oracle;
- acesso somente por endpoints autorizados da aplicação;
- diretório fora dos arquivos estáticos e não servido pelo WhiteNoise.

## 3. Aplicações Django

Estrutura incremental adotada:

```text
apps/
├── accounts/
├── core/
├── evidence/
├── offboarding/
├── pending_items/
├── sectors/
├── system_settings/
├── templates_engine/
└── integrations/
    ├── active_directory/
    └── senior/

frontend/
└── src/app/
    ├── core/       auth, config, layout, theme
    └── features/   uma pasta por tela
```

Novos módulos serão criados somente quando o respectivo checkpoint exigir.
`accounts` contém conta local, papel funcional, escopos, services, autorização, API e
auditoria de contas. `core` contém os endpoints operacionais e a view que serve
a SPA. `integrations/active_directory` contém configuração tipada, cliente
LDAP somente leitura, backend de autenticação e verificação operacional.
`integrations/senior` contém SQL, DTOs e o repository somente leitura. Não
existem models para objetos do AD ou do Senior.
`system_settings` contém o singleton LDAP, criptografia de segredo, validação
X.509, services auditados e a API exclusiva de SuperAdmin.
`sectors` contém os incrementos de setores e responsáveis: cobertura
global/empresa/filial, validade, versão otimista, revogação lógica, bloqueio
pessimista nas mutações críticas, auditoria append-only, services, API e
administração técnica somente leitura.
`templates_engine` contém cabeçalhos estáveis e versões de templates, perguntas
e grupos, com edição auditada do `DRAFT` e publicação imutável. Templates são
neutros quanto a setor; cada regra de grupo associa separadamente um setor a
uma versão exata de template. `offboarding` contém abertura, seleção versionada
do rascunho e início idempotente: snapshots do colaborador, setor,
template e perguntas, tarefas pertencentes ao setor, auditoria append-only,
services, API e administração técnica somente leitura.
`pending_items` contém pendências, seus itens, comentários append-only,
regularização, classificação de bloqueio, concorrência, idempotência e
auditoria. `evidence` mantém metadados e SHA-256 no Oracle, grava os bytes no
storage privado, valida extensão/MIME/assinatura e expõe somente upload e
download autorizados; nenhum caminho privado é projetado.

Setores, templates, grupos e perguntas são entidades configuráveis locais e
usam o próprio `ID` como código público numérico. O service cria o registro,
obtém o identificador do banco e preenche a coluna técnica `CODE` na mesma
transação. A SPA e os serializers não aceitam código manual. Essa convenção não
altera referências externas do Senior nem os códigos funcionais fixos.

A estrutura de `frontend/` está preservada no plano concluído em
`history/completed-plans/MIGRATION_FRONTEND_SPA.md` §5.

## 4. Serviços de domínio

Regras críticas devem ficar fora de views e signals genéricos.

Serviços administrativos implementados:

- `CreateUserService`
- `UpdateUserService`
- `ResetPasswordService`
- `AssignRoleService`
- `RevokeRoleService`
- `LinkDirectoryIdentityService`
- `CreateUserFromDirectoryService`
- `UnlinkAdIdentityService`

Serviços de workflow implementados na Fase 4:

- `OpenOffboardingProcessService`;
- `UpdateDraftSelectionService`;
- `GetDraftProcessContextService`;
- `StartOffboardingProcessService`;
- `StartSectorTaskService`;
- `CompleteSectorTaskService`.

Serviços de workflow implementados na Fase 5:

- `CreatePendingItemService`;
- `AddPendingCommentService`;
- `ChangePendingStatusService`;
- `UploadEvidenceService`;
- `RegisterEvidenceDownloadService`.

Serviços de workflow planejados para as fases 6 a 9:

- `EvaluateProcessReadinessService`
- `ReleaseForTerminationService`
- `CloseOffboardingProcessService`
- `EscalateOverdueTasksService`

Serviços funcionais implementados na Fase 3:

- `CreateSectorService`;
- `UpdateSectorService`.

Ambos exigem `sectors.manage_sectors` com concessão global e executam em
transação. Rejeitam ciclos de escalada e sincronizam zero ou mais responsáveis
como filhos do agregado. Setor, usuários e associações são bloqueados em ordem;
o vínculo persiste somente usuário e validade, herda o escopo do setor e
registra antes/depois na auditoria append-only com motivo padronizado pelo
servidor. Não existe service ou endpoint independente para manter a
responsabilidade.

`OpenOffboardingProcessService` consulta o Senior antes de iniciar a transação
de escrita e nunca persiste referência retornada pela listagem. Depois da
releitura da chave completa, bloqueia ator e atribuições `DP`, repete
`has_effective_role()` no escopo, impede outro processo não encerrado para a
mesma identidade e confirma processo, snapshot e `PROCESS_OPENED` na mesma
transação. Revogação de `DP` e abertura concorrentes têm vencedor
determinístico; falha da auditoria desfaz toda a abertura.

`UpdateDraftSelectionService` substitui grupos e ajustes manuais sob lock e
versão otimista, fixando as versões publicadas. `StartOffboardingProcessService`
não consulta o Senior: trava o agregado, resolve o escopo, revalida `DP` e
responsáveis vigentes, cria tarefas/perguntas históricas e registra
`PROCESS_STARTED` e a chave idempotente na mesma transação. A ordenação de
locks acompanha Setor → responsabilidades → usuários para evitar inversão com
a manutenção do catálogo.

`sector_tasks_for_actor()` limita usuários funcionais ao vínculo vigente com o
setor e ao escopo herdado que cobre empresa/filial do processo. Para
SuperAdmin ativo, devolve todas as tarefas. `StartSectorTaskService` e
`CompleteSectorTaskService` revalidam sob locks a responsabilidade ou a
autoridade global, exigem estado, versão e chave idempotente e gravam tarefa,
respostas e auditoria na mesma transação. A conclusão valida o snapshot de
cada pergunta; valores das respostas não são copiados para o evento de
auditoria.

No Oracle 19c, `JSONField` usa constraint `IS JSON`, que rejeita um escalar
JSON no topo. Por isso `RESPONSE` armazena internamente o documento
`{"value": ...}`; a API projeta novamente o valor simples. Esse detalhe é
isolado no backend e não cria regra de negócio no Angular.

`TextField` é armazenado como `NCLOB` no Oracle. Consultas que carregam models
com esse tipo não usam `SELECT DISTINCT`, porque o Oracle não compara LOBs
nessa operação. A seleção de grupos aplicáveis e a autorização da listagem de
tarefas eliminam duplicidade com subconsultas correlacionadas `EXISTS`.

O backend Oracle também não aceita paginação em uma consulta
`SELECT ... FOR UPDATE`. Consultas de replay idempotente bloqueiam o conjunto
definido por uma constraint única e o materializam sem `.first()`, `.last()` ou
slice; isso evita que o ORM acrescente `FETCH FIRST` ao lock.

### Consulta ao Senior

- endpoints chamam o repository de consulta;
- o repository usa cursor Oracle e SQL `SELECT` parametrizado;
- não existem models Django, models não gerenciados ou tabelas `REF_*` para objetos do Senior;
- a conexão de runtime do SGPD recebe grants explícitos apenas nos objetos `VETORH` homologados;
- SQL não fica espalhado em serializers ou endpoints;
- a abertura do processo copia o resultado autorizado para o snapshot histórico do SGPD.

## 5. Eventos de domínio

Eventos planejados com o workflow:

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

A SPA consome os quatro endpoints na rota `/fe/colaboradores`, cancela
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
empresa e filial do usuário autenticado. Ele orienta a navegação da SPA; a
decisão de autorização continua sendo aplicada em cada endpoint e em cada
service.

Endpoints de contas implementados:

```text
GET  POST   /api/v1/accounts/users/
GET  PATCH  /api/v1/accounts/users/{id}/
POST        /api/v1/accounts/users/{id}/reset-password/
POST        /api/v1/accounts/users/{id}/roles/
POST        /api/v1/accounts/users/{id}/ad-link/
POST        /api/v1/accounts/users/{id}/ad-unlink/
POST        /api/v1/accounts/role-assignments/{id}/revoke/
GET         /api/v1/accounts/roles/
GET         /api/v1/accounts/roles/{id}/
GET         /api/v1/accounts/audit/
GET         /api/v1/accounts/directory/status/
GET         /api/v1/accounts/directory/groups/?q=
GET         /api/v1/accounts/directory/users/?q=
POST        /api/v1/accounts/directory/users/create/
```

Endpoints de configuração técnica, todos exclusivos de SuperAdmin:

```text
GET  PUT /api/v1/settings/ldap/
POST     /api/v1/settings/ldap/validate/
POST     /api/v1/settings/ldap/certificate/
POST     /api/v1/settings/ldap/certificate/validate/
POST     /api/v1/settings/ldap/connection-test/
```

Além da proteção redundante na API e nos services, a ativação do login AD exige
fingerprint de probe correspondente à configuração e à CA vigentes. A senha e
o caminho privado não aparecem em payloads nem em eventos.

Cada endpoint valida entrada, invoca o service correspondente e traduz o
resultado. Nenhum implementa regra de negócio.

`POST /api/v1/accounts/users/` aceita uma designação inicial opcional em
`initial_role`, somente para `DP`, com escopo organizacional. O
`CreateUserService` compõe a criação com o `AssignRoleService` dentro da mesma
transação: a operação simples continua exigindo `manage_users`; ao incluir o
papel, `manage_roles` também é revalidada no service. Conta, atribuição e seus
dois eventos de auditoria são confirmados ou desfeitos em conjunto.

O `AssignRoleService` aceita somente `DP` e também atende
criação, reativação e atualização de validade da atribuição. Esses fluxos não
recebem justificativa digitada e auditam um motivo operacional padronizado. A
revogação continua isolada no `RevokeRoleService`, sem justificativa digitada
e com motivo padronizado.
Criação e edição dinâmica de papéis, o catálogo de permissões e a tela
`/fe/papeis` não possuem superfície ativa.

`has_effective_role()` é o limite reutilizável para os services do workflow:
para usuários funcionais, o papel `DP` deve estar ativo, vigente e cobrir a
empresa/filial do processo; para SuperAdmin ativo, a ADR-044 concede autoridade
global explícita. `DP` recebe `query_senior_references`.

A API emite `account_role_assignment_requested` ao receber a operação e
`account_role_assignment_completed` após o commit do service. O cadastro
composto emite `account_user_creation_requested` e
`account_user_creation_completed`, incluindo o indicador técnico de papel
inicial. Esses logs carregam correlation ID e somente IDs, escopo e resultado;
payload, login, e-mail e senha não são projetados.

A autorização é declarada por endpoint e reavaliada a cada requisição:
`manage_users` para usuários e senha, `manage_roles` somente para atribuir ou
revogar os papéis fixos, `link_ad_identity` para o vínculo com o AD e
`view_account_audit` para a auditoria. O service revalida a mesma permissão no
próprio limite, conforme a ADR-024, de modo que a checagem do endpoint é
redundante por decisão e não é o único guarda.

Descoberta e importação AD são explicitamente administrativas. As buscas
validam e escapam a entrada, aplicam paginação e limite, excluem contas
desabilitadas e podem restringir por OU, grupo direto ou grupo aninhado. O
service de criação exige simultaneamente `link_ad_identity` e `manage_users`,
revalida a identidade por `objectGUID`, cria a conta com senha inutilizável e
gera os eventos `USER_CREATED` e `AD_LINKED` na mesma transação. O POST recebe
somente o identificador selecionado; a auditoria usa motivo padronizado, sem
exigir justificativa manual. Nenhum papel é atribuído automaticamente.

O payload administrativo de usuário projeta a política efetiva
`local_password_allowed`. Quando o login AD está ativo, o service de senha e a
SPA bloqueiam redefinição para conta comum vinculada; a exceção é calculada
pela mesma configuração de contingência usada pelo backend de autenticação.

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
| `directory_not_configured` | 503 | integração AD desabilitada ou incompleta |
| `directory_unavailable` | 503 | AD, bind ou TLS indisponível |
| `directory_contract_error` | 502 | atributos retornados fora do contrato |
| `directory_identity_not_found` | 404 | identidade não elegível ou inexistente |
| `senior_unavailable` | 503 | Senior HCM indisponível |
| `senior_contract_error` | 502 | resposta inválida da fonte cadastral |

Requisição sem sessão recebe `401`, e não o `403` que o DRF produziria por
`SessionAuthentication` não publicar cabeçalho `WWW-Authenticate`. A distinção
permite à SPA rotear para o login em vez de exibir erro, e separa "autentique-se"
de "você não pode".

Endpoints de abertura implementados:

```text
GET  /api/v1/processes/?status=&open=&completed=&offset=&limit=
POST /api/v1/processes/
GET  /api/v1/processes/{uuid}/tasks/?status=&offset=&limit=
GET  /api/v1/processes/{uuid}/draft/
PUT  /api/v1/processes/{uuid}/draft/selection/
POST /api/v1/processes/{uuid}/start/
```

O `GET` lista somente processos cobertos pelos escopos `DP` vigentes do ator;
SuperAdmin recebe todos. Aceita filtro pelos estados já implementados,
paginação sem `COUNT(*)` e ordena pela abertura mais nova. O filtro
`open=true` reúne processos `INICIADO` com ao menos uma tarefa não concluída.
O filtro `completed=true` reúne processos
formalmente `ENCERRADO` e processos `INICIADO` que possuem ao menos uma tarefa
setorial e nenhuma tarefa não concluída. Nesse filtro, a conclusão setorial
mais nova aparece primeiro; até existir a data formal de encerramento, um
encerrado sem tarefa concluída usa a abertura como desempate. A consulta usa
subqueries correlacionadas e `EXISTS`, evitando agregação sobre os campos
históricos `NCLOB` no Oracle. `status`, `open` e `completed` são mutuamente
exclusivos. O `POST` cria somente `RASCUNHO`; não existe
`DELETE`. A listagem de tarefas por UUID revalida a autoridade `DP` no escopo
do processo e devolve resumos sob demanda, sem depender da responsabilidade
setorial do coordenador; ela alimenta a expansão dos processos em aberto e
concluídos na SPA. Os demais endpoints por UUID consultam/substituem a seleção
e iniciam o processo. O início exige
`Idempotency-Key`: repetição pelo mesmo ator e corpo recupera o resultado;
reutilização divergente responde `409 Conflict` com o código
`idempotency_conflict`.

Endpoints de tarefa implementados:

```text
GET  /api/v1/tasks/
GET  /api/v1/tasks/{id}/
POST /api/v1/tasks/{id}/start/
POST /api/v1/tasks/{id}/complete/
```

Listagem e detalhe são limitados pela responsabilidade efetiva do setor. Início
e conclusão exigem `Idempotency-Key` e versão esperada; conflito de chave
responde `409`, tarefa fora do escopo responde `404` e falha de regra mantém o
envelope padronizado da API. A SPA separa ativas de concluídas em dois cards;
as concluídas são ordenadas por `COMPLETED_AT` decrescente.

Endpoints de domínio planejados:

```text
GET  /api/v1/processes/{uuid}/
POST /api/v1/processes/{uuid}/release/
POST /api/v1/processes/{uuid}/cancel/

```

Endpoints da Fase 5 implementados:

```text
GET  POST /api/v1/pending-items/
POST      /api/v1/pending-items/{uuid}/status/
POST      /api/v1/pending-items/{uuid}/comments/
GET  POST /api/v1/evidence/
GET       /api/v1/evidence/{uuid}/download/
```

Listagem, mutação, upload e download aceitam a autoridade vigente do setor ou
do `DP` no escopo do processo; SuperAdmin usa a autoridade global da ADR-044.
As mutações revalidam o limite sob locks. O upload exige
`Idempotency-Key`, não expõe caminho e remove o arquivo recém-gravado caso a
transação ou a auditoria falhe.

Endpoints de configuração funcional implementados:

```text
GET  POST  /api/v1/sectors/
GET  PATCH /api/v1/sectors/{id}/
GET         /api/v1/sectors/responsible-candidates/
GET         /api/v1/workflow-config/sectors/
GET  POST   /api/v1/workflow-config/templates/
POST        /api/v1/workflow-config/templates/{id}/versions/
PUT         /api/v1/workflow-config/template-versions/{id}/
POST        /api/v1/workflow-config/template-versions/{id}/publish/
GET  POST   /api/v1/workflow-config/groups/
POST        /api/v1/workflow-config/groups/{id}/versions/
PUT         /api/v1/workflow-config/group-versions/{id}/
POST        /api/v1/workflow-config/group-versions/{id}/publish/
GET  POST   /api/v1/workflow-config/applicability-rules/
PUT         /api/v1/workflow-config/applicability-rules/{id}/
```

As regras de aplicabilidade sugerem grupos pelo snapshot do processo e não
substituem a seleção do `DP`: o rascunho devolve `applicability_suggestion` com
os grupos sugeridos e a regra de origem, a SPA pré-marca essa lista e nada é
persistido antes de o `DP` salvar a seleção. Toda regra vigente que casa
contribui seu grupo — a prioridade só ordena a exibição, conforme a ADR-046.

Não existe `DELETE`: a desativação é uma alteração explícita, versionada e
auditada. A cobertura usa escopos `GLOBAL`, `COMPANY` e `BRANCH`; um escopo
global não pode coexistir com escopos específicos e uma filial não é repetida
quando toda a empresa já está coberta. O payload de criação/alteração do setor
contém a lista completa de responsáveis. Cada vínculo é único por usuário e
setor, possui validade e versão, é revogado sem exclusão, herda o escopo do
setor e deriva `RESPONSAVEL_SETOR` enquanto estiver efetivo. Não existe
coordenador ou substituto.

Os contratos `workflow-config` exigem
`templates_engine.manage_workflow_configuration`. Publicar aposenta a versão
vigente anterior sem alterar seu conteúdo; cada versão de grupo fixa uma
versão exata de template por setor. A mesma versão pode ser reutilizada por
quantos setores forem necessários, sem duplicar seu conteúdo.

Setores, templates, grupos e perguntas usam o próprio `ID` como código público
numérico, sem campo correspondente nos payloads de criação. Templates aceitam
busca parcial por nome no parâmetro `q`, hoje usada somente pela API: a SPA
lista o catálogo completo. Versões `DRAFT` de template e grupo
podem ser editadas atomicamente; os services bloqueiam cabeçalho, versões e
itens/regras, exigem a versão otimista e auditam a substituição do conteúdo.
Uma versão publicada permanece imutável. Para templates publicados, a SPA cria
um novo rascunho clonado antes de editá-lo.

Todos os responsáveis efetivos do setor receberão a mesma notificação e terão
a mesma autoridade. No workflow futuro, mutações de tarefa deverão bloquear ou
versionar o estado crítico e possuir chave de idempotência: a primeira
transação válida confirma a ação; as demais observam o novo estado sem
duplicar auditoria, e-mail ou efeito financeiro.

Com a ADR-025 e a conclusão da Fase G, a API é a única superfície funcional da
aplicação. Comandos de gestão também podem chamar services diretamente,
preservando a autorização no limite do caso de uso.

## 7. Observabilidade

Implementado:

- logs JSON configurados na saída padrão;
- correlation ID aceito em `X-Correlation-ID` ou gerado pela aplicação e
  devolvido na resposta;
- health checks separados em liveness e readiness;
- registro de duração, quantidade de linhas e falhas das consultas ao Senior.
- recebimento e conclusão da criação de conta e da designação de papel, com
  metadados técnicos seguros para diferenciar ausência de requisição de falha
  transacional.

Planejado com os módulos de workflow e processamento assíncrono:

- métricas de tarefas;
- monitoramento de filas;
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
