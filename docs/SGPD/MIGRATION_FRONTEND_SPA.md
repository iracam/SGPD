# Migração da interface para SPA Angular

## 0. Estado deste documento

Plano aprovado em 2026-07-28. Fases A a G concluídas.
O andamento detalhado está no checkpoint 2.5 de `CHECKPOINT.md`.

Este documento é o registro do plano executado que substituiu a interface
server-side por uma SPA Angular. As seções de diagnóstico descrevem o estado
encontrado no início da migração e não representam componentes atuais. A
migração não alterou Oracle, migrations, quota, contrato SQL do Senior,
services de domínio ou autorização.

## 1. Decisões aprovadas

| Tema | Decisão | ADR |
| --- | --- | --- |
| Interface | SPA Angular 21 substitui Django Templates + HTMX + Alpine | ADR-025 |
| Autenticação | Sessão Django + CSRF em origem única; sem JWT e sem token no navegador | ADR-026 |
| Biblioteca de UI | PrimeNG 21 com preset Aura e primeicons | ADR-027 |
| Entrega | `ng build` servido pelo Django/WhiteNoise; `ng serve` com proxy no desenvolvimento | ADR-027 |
| Escopo | Substituição total: administração de contas e cascata Senior | ADR-025 |
| Responsividade | Mobile first como requisito, não como adaptação | ADR-028 |
| Django Admin | Preservado, somente leitura, conforme `SECURITY.md` §9 | — |

O projeto de referência estrutural é `/home/macari/dev/prdcana/frontend`
(CanaLOG Web). Dele são reaproveitados a estrutura de diretórios, o roteamento
em dois níveis, o modelo de estado por signals, o contrato do menu, o serviço de
tema e a arquitetura de autenticação.

Duas características daquele projeto **não** são reaproveitadas:

- a mecânica de autenticação por JWT, substituída por sessão conforme a
  ADR-026;
- a metodologia de CSS desktop first, substituída por mobile first conforme a
  ADR-028. A referência escreve o layout para desktop e o degrada com
  `@media (max-width: ...)`; o SGPD escreve para o menor viewport e o promove
  com `@media (min-width: ...)`.

## 2. Diagnóstico inicial

### 2.1 Componentes substituídos

| Item | Arquivos | Linhas |
| --- | --- | --- |
| Templates | `templates/` completo: `base.html`, `403.html`, sete de `accounts/`, `senior/selection.html` e quatro parciais | 14 arquivos |
| Views HTML | `apps/accounts/views.py`, `apps/integrations/senior/views.py`, `apps/integrations/senior/ui_urls.py` | 838 |
| Suporte à UI | `apps/accounts/forms.py`, `apps/accounts/context_processors.py` | 187 |
| Runtime do navegador | `static/vendor/htmx/` e o `staticfiles/` gerado | — |
| Testes acoplados à UI | `tests/test_senior_ui.py`, `tests/test_accounts_views.py` | 410 |

### 2.2 Componentes preservados

`apps/accounts/services.py`, `apps/accounts/authorization.py`,
`apps/accounts/models.py`, `apps/accounts/admin.py`, as migrations,
`apps/integrations/senior/repository.py`, `queries.py`, `dto.py`,
`exceptions.py`, `permissions.py`, além de `tests/test_accounts_services.py`,
`tests/test_senior_repository.py`, `tests/test_senior_api.py` e
`tests/test_user_model.py`.

A ADR-024 determina que cada service administrativo valide a permissão do ator
no próprio limite do caso de uso, sem depender da camada chamadora. Essa
decisão é o que tornou a migração segura: a API é uma casca fina sobre services
já protegidos, e não uma segunda implementação das regras.

### 2.3 Lacuna identificada

A cascata Senior já possuía quatro endpoints JSON autenticados e autorizados por
escopo em `/api/v1/references/`, que foram diretamente reaproveitados.

A administração de contas não possuía API: eram catorze views de formulário
server-side. A Fase C resolveu essa lacuna antes da remoção da Fase G.

## 3. Arquitetura implementada

```text
Navegador
    |
    +-- SPA Angular 21 (PrimeNG 21 + Aura)
            |
            |  mesma origem; cookie de sessão HttpOnly + cabeçalho X-CSRFToken
            v
        Django 5.2
            |
            +-- view catch-all  --> frontend/dist/frontend/browser/index.html
            +-- WhiteNoise      --> assets Angular com hash próprio
            +-- /api/v1/auth/
            +-- /api/v1/accounts/
            +-- /api/v1/references/
            +-- /health/
            +-- /admin/                (somente leitura)
                    |
                    v
            services + authorization  (inalterados)
                    |
                    v
            Oracle 19c: schema SGPD e SELECT em VETORH
```

Não há CORS, token no navegador, proxy reverso nem Nginx. A ADR-014 permanece
válida.

## 4. Superfície de API implementada

### 4.1 Autenticação e contexto — `/api/v1/auth/`

| Método | Rota | Origem da regra |
| --- | --- | --- |
| `GET` | `csrf/` | `ensure_csrf_cookie` |
| `POST` | `login/` | `record_authentication_event` (`LOGIN`, `LOGIN_FAILED`) |
| `POST` | `logout/` | `record_authentication_event` (`LOGOUT`) |
| `GET` | `me/` | inclui `must_change_password` |
| `GET` | `context/` | `has_permission` e `allowed_company_codes` |
| `POST` | `change-password/` | `ChangeOwnPasswordService` |

`GET context/` devolve papéis, permissões efetivas, escopos de empresa e filial
e as chaves de funcionalidade que governam a visibilidade do menu. A permissão
é resolvida pelo servidor a cada sessão.

### 4.2 Contas — `/api/v1/accounts/`

| Método | Rota | Service |
| --- | --- | --- |
| `GET`, `POST` | `users/` | `CreateUserService` |
| `GET`, `PATCH` | `users/{id}/` | `UpdateUserService` |
| `POST` | `users/{id}/reset-password/` | `ResetPasswordService` |
| `POST` | `users/{id}/roles/` | `AssignRoleService` |
| `POST` | `users/{id}/ad-link/` | `LinkAdIdentityService` |
| `POST` | `users/{id}/ad-unlink/` | `UnlinkAdIdentityService` |
| `POST` | `role-assignments/{id}/revoke/` | `RevokeRoleService` |
| `GET` | `roles/` | catálogo fixo atribuível somente `DP` |
| `GET` | `roles/{id}/` | detalhe de papel do catálogo fixo |
| `GET` | `audit/` | `AccountAuditEvent`, paginado |

Nenhum endpoint implementa regra de negócio. Cada um valida entrada, invoca o
service correspondente e traduz o resultado.

No cadastro manual, `POST users/` pode receber `initial_role` para `DP`. A SPA
oferece o papel e o escopo somente a quem
possui `manage_roles`; o backend repete essa
autorização e grava conta e designação atomicamente. Após a criação, a tela
abre o detalhe do usuário, onde outras atribuições podem ser mantidas.
Inclusões e alterações cadastrais, inclusive designações, revogações, senha e
vínculo AD, não exibem nem enviam justificativa livre; a auditoria usa motivo
operacional e dados estruturados do servidor.

Os botões de confirmação dos diálogos chamam explicitamente a ação Angular por
`onClick`; o `ngSubmit` é mantido para envio por teclado. Essa redundância evita
que a encapsulação do botão PrimeNG suprima silenciosamente o submit. Formulário
inválido e falha no catálogo de papéis sempre exibem uma mensagem e não simulam
sucesso. A API registra o recebimento e a conclusão da designação em log JSON
correlacionado, sem dados pessoais.

### 4.2.1 Setores — `/api/v1/sectors/`

| Método | Rota | Contrato |
| --- | --- | --- |
| `GET`, `POST` | `/api/v1/sectors/` | setor com escopos e lista completa de responsáveis |
| `GET`, `PATCH` | `/api/v1/sectors/{id}/` | detalhe e sincronização atômica do agregado |
| `GET` | `/api/v1/sectors/responsible-candidates/` | usuários ativos elegíveis |

O formulário contém um card repetível de responsáveis com usuário, início e
fim da validade. Não há escopo no card: cada vínculo herda os escopos do setor.
A lista indica responsável vigente e agendamentos futuros. A manutenção
independente `/fe/responsaveis` e sua API foram removidas.

### 4.3 Requisitos transversais

**Envelope de erro.** Todas as respostas de erro seguem
`{"code": ..., "message": ..., "details": ...}`. Um `exception_handler` do DRF
traduz o `ValidationError` do Django — que os services levantam com
`message_dict` — em `400` com erros por campo.

**Senha temporária.** Sob `/api/`, `PasswordChangeRequiredMiddleware` devolve
`403 {"code": "password_change_required"}`; navegação direta é redirecionada
para `/fe/senha`.

**Limitação de tentativas.** O login usa throttling do DRF e continua
registrando `LOGIN_FAILED`.

**Concorrência.** `expected_version` é exposto como campo do payload,
preservando a rejeição de escrita concorrente definida na ADR-024.

**Paginação.** As listas de contas e a cascata Senior usam paginação explícita
por `offset`/`limit`, sem `COUNT(*)`, conforme `ARCHITECTURE.md` §6.

## 5. Frontend

### 5.1 Estrutura

`frontend/` na raiz do repositório, com `angular.json`, `tsconfig*.json`,
`.editorconfig`, `proxy.conf.json` e `package.json` espelhados do projeto de
referência. Angular 21 standalone, estado por signals, sem NgModules e sem
biblioteca de gerência de estado.

```text
frontend/src/app/
├── app.config.ts
├── app.routes.ts
├── fe.routes.ts
├── app.ts
├── core/
│   ├── api/      api-error
│   ├── auth/     auth.service, auth.guard, auth.interceptor,
│   │             auth.initializer, auth.context, auth.constants
│   ├── config/   api.config.ts
│   ├── layout/   authenticated-layout, layout.service, layout.types
│   └── theme/    theme.service.ts
└── features/
    ├── login/
    ├── painel/
    ├── senha/
    ├── colaboradores/
    ├── usuarios/
    ├── papeis/
    ├── auditoria/
    └── configuracoes/
```

Cada feature possui componente, template e SCSS; service e models próprios são
adicionados quando há acesso a API ou contrato de dados específico.

### 5.2 Roteamento

O roteamento usa dois níveis: `app.routes.ts` redireciona para `fe` e carrega
`fe.routes.ts` de forma lazy; `fe.routes.ts` declara o login como rota pública
e, em seguida, uma rota protegida por `authGuard` que usa
`AuthenticatedLayout` como componente pai dos filhos autenticados. Todas as
páginas usam `loadComponent` e declaram `title`.

| Rota | Página |
| --- | --- |
| `/fe/login` | autenticação local |
| `/fe/painel` | painel inicial |
| `/fe/colaboradores` | cascata Empresa → Filial → Tipo → Colaborador |
| `/fe/setores` | cadastro de setores, escopos e múltiplos responsáveis |
| `/fe/usuarios`, `/fe/usuarios/:id` | administração de usuários |
| `/fe/auditoria` | auditoria de contas |
| `/fe/configuracoes` | cards técnicos, somente SuperAdmin |
| `/fe/configuracoes/autenticacao` | LDAP, CA e testes, somente SuperAdmin |
| `/fe/senha` | troca da própria senha |

### 5.3 Autenticação

A arquitetura usa `AuthService` com signals, `authGuard`, `authInterceptor`,
`authInitializer`, `SKIP_AUTH_REDIRECT` como `HttpContextToken` e
`api.config.ts` com as rotas tipadas.

| Referência (JWT) | SGPD (sessão) |
| --- | --- |
| `Authorization: Bearer <access>` | `X-CSRFToken` e `withCredentials` |
| `refreshAccessToken()` em `401` | `401` encerra a sessão e roteia para o login |
| par de tokens em `localStorage` | nenhum dado de sessão em `localStorage` |
| `initializeSession()` via refresh | `initializeSession()` via `GET /auth/me/` |

O `localStorage` continua sendo usado apenas para preferências de interface:
estado colapsado da navegação e tema.

### 5.4 Menu

O contrato `NavItem[]` usa `label`, `route`, `icon`, `description`, `feature`
e, quando necessário, `role`, com `visibleNavItems` filtrando pelo contexto
devolvido por `GET /auth/context/`.

| Item | Rota | Ícone | Permissão |
| --- | --- | --- | --- |
| Painel | `/fe/painel` | `pi pi-th-large` | — |
| Abrir processo | `/fe/colaboradores` | `pi pi-folder-plus` | `query_senior_references` + papel `DP` |
| Setores | `/fe/setores` | `pi pi-building` | `manage_sectors` |
| Usuários | `/fe/usuarios` | `pi pi-users` | `manage_users` |
| Auditoria | `/fe/auditoria` | `pi pi-history` | `view_account_audit` |
| Configurações | `/fe/configuracoes` | `pi pi-cog` | `is_superuser` |

O menu e a rota de manutenção de papéis foram removidos em 2026-07-29. O
catálogo atribuível é fixo em `DP`; `RESPONSAVEL_SETOR` é derivado do vínculo
mantido no card de responsáveis do setor. A rota independente
`/fe/responsaveis` também foi removida.

A rota `/fe/colaboradores` foi promovida na Fase 4: preserva a cascata e
acrescenta gestor, datas, motivo, prioridade, observações e confirmação da
abertura. O papel `DP` orienta a visibilidade do menu; o service continua sendo
o limite real de autorização. Grupos, templates, listagem de processos,
pendências, valores e liberação entram conforme os próximos checkpoints.

A sidebar é colapsável com estado persistido, e o rodapé mantém o painel de
sessão, o acesso à troca da própria senha, o alternador de tema claro/escuro e
a saída.

### 5.5 Mobile first

Requisito do projeto: a interface é escrita para o menor viewport e ampliada a
partir dele. Todo SCSS de layout usa exclusivamente `@media (min-width: ...)`.
Nenhuma consulta `max-width` é aceita em código novo — a presença de uma indica
que a regra base foi escrita para desktop.

#### Pontos de quebra

| Nome | Largura | Alvo |
| --- | --- | --- |
| base | 0 | telefone em retrato, a partir de 360 px |
| `sm` | 480 px | telefone em paisagem |
| `md` | 768 px | tablet |
| `lg` | 1024 px | desktop; promove a navegação a barra lateral fixa |
| `xl` | 1440 px | desktop amplo |

Os pontos de quebra são declarados uma única vez, como tokens em
`styles.scss`, e consumidos por todas as features.

#### Consequências estruturais

**Navegação.** O estado base é uma barra superior compacta com gaveta lateral
sobreposta, controlada por `mobileNavOpen`. A partir de `lg`, a gaveta é
promovida a barra lateral permanente e o estado colapsado de `LayoutService`
passa a valer. Na referência a relação é inversa: a barra lateral é o padrão e
vira topbar abaixo de 1024 px.

A gaveta fecha ao navegar, fecha com `Escape`, prende o foco enquanto aberta e
devolve o foco ao botão que a abriu.

**Tabelas.** Usuários e auditoria são tabulares e uma `p-table` com
muitas colunas é inutilizável em telefone. Cada listagem tem duas
representações a partir dos mesmos dados: lista de cartões no estado base, com
os campos essenciais e as ações principais; tabela completa a partir de `md`.
Nenhuma tela produz rolagem horizontal no `body`; quando uma tabela precisar
rolar, ela rola dentro do próprio contêiner.

**Formulários.** Coluna única no estado base, com rótulo acima do campo e
controles em largura total. Múltiplas colunas apenas a partir de `md`. As ações
de submissão ficam ao alcance do polegar, sem exigir rolagem até o rodapé em
formulários longos.

**Cascata Senior.** Os quatro seletores empilham no estado base. A busca de
colaborador usa o filtro do `p-select` em largura total, com teclado adequado e
sem exigir precisão de ponteiro.

**Tipografia e zoom.** A referência usa `html { font-size: 14px }`. No SGPD a
raiz é 16 px no estado base e passa a 14 px somente a partir de `lg`,
preservando a densidade do desktop. Campos de formulário nunca são renderizados
abaixo de 16 px em telefone: abaixo disso, o Safari no iOS aplica zoom
automático ao foco e desloca o layout.

**Alvos de toque.** Mínimo de 44 × 44 px para qualquer elemento interativo no
estado base, incluindo ações dentro de listas e cartões. Os padrões do PrimeNG
ficam abaixo disso e são ajustados por token.

Em `lg`, campos de edição e botões de uma linha usam a mesma altura compacta de
`2.25rem`, centralizada no token global `--control-height`. No estado base,
ambos preservam os 44 px exigidos para telas de toque.

**Peso.** O orçamento de build permanece em 600 kB de aviso e 1 MB de erro para
o bundle inicial, agora com justificativa de rede móvel. Toda página é
carregada por `loadComponent`.

#### Piso de qualidade

Foco de teclado visível, `prefers-reduced-motion` respeitado, contraste
suficiente nos temas claro e escuro, e ausência de rolagem horizontal no `body`
em qualquer ponto de quebra.

### 5.6 Identidade visual

A arquitetura de tokens de `styles.scss` é mantida integralmente: mesmas
famílias tipográficas, mesmo tratamento de fundo, mesmo modo escuro e mesmo
conjunto de variáveis `--p-*` do PrimeNG. Mudam os valores da marca e a escala
tipográfica base definida em §5.5.

| Token | CanaLOG | SGPD |
| --- | --- | --- |
| fundo do shell | `#1d3241` | `#232733` |
| acento | `#f1d75d` | `#4fb3a5` |
| contraste do acento | `#1b2f3d` | `#10231f` |
| fundo da página, claro | `#eef4f8` | `#eef1f4` |
| marca | `CL` | `DF` |

A escolha de grafite e verdigris parte do domínio: o SGPD trata de verificação e
liberação, não de colheita. O acento é a cor do item conferido e será
reaproveitado nos tokens de estado do processo — pendente, em análise,
bloqueado, liberado e cancelado — exigidos pelas Fases 4 a 6.

Manter uma identidade própria também evita que dois sistemas corporativos
distintos fiquem indistinguíveis para quem usa ambos.

### 5.7 Entrega

`ng build` gera `frontend/dist/frontend/browser/`. Os assets são servidos pelo
WhiteNoise a partir de `WHITENOISE_ROOT`; o Angular já aplica hash próprio aos
arquivos. O pipeline `collectstatic` permanece dedicado aos assets do Django
Admin.

O `index.html` é servido por uma view Django dedicada, decorada com
`ensure_csrf_cookie`, registrada como catch-all **depois** de `/api/`,
`/admin/`, `/health/` e `/static/`.

Servir o `index.html` pelo próprio WhiteNoise não funciona:
`CompressedManifestStaticFilesStorage` renomeia o arquivo incluindo hash, o que
quebra a rota `/`.

Durante o desenvolvimento, `ng serve --proxy-config proxy.conf.json` encaminha
`/api` e `/admin` ao Django.

## 6. Sequência de execução

A ordem executada foi **API primeiro, remoção por último**. A interface
server-side foi removida somente depois que a SPA cobriu a funcionalidade
equivalente, de modo que cada etapa deixou o sistema utilizável, conforme
AGENTS.md §12.

| Fase | Entrega | Validação |
| --- | --- | --- |
| A | ADR-025, ADR-026, ADR-027, ADR-028 e atualização de `AGENTS.md`, `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `ENVIRONMENT.md`, `ROADMAP.md`, `CHECKPOINT.md` e `MANIFEST.json` | Nenhum código; consistência documental e manifesto |
| B | API de autenticação e contexto, exception handler, middleware adaptado, throttling do login | pytest, ruff, mypy |
| C | API de contas: usuários, papéis, atribuições, vínculo AD, permissões e auditoria | pytest com caso feliz, `401`, `403`, `400`, versão otimista e auditoria por endpoint |
| D | Scaffold Angular, PrimeNG e Aura, tokens do SGPD e pontos de quebra, `core/auth`, shell com gaveta móvel, login e integração do build com o Django | vitest e conferência visual em 360, 390, 768, 1024 e 1440 px |
| E | Features de contas: usuários, papéis, auditoria e senha, com cartões no estado base e tabela a partir de `md` nas listagens | vitest e conferência visual nos cinco pontos de quebra |
| F | Feature da cascata Senior sobre os quatro endpoints existentes | smoke somente leitura contra o Oracle DEV e conferência visual nos cinco pontos de quebra |
| G | Remoção de templates, views HTML, forms, context processors, `ui_urls`, HTMX e testes antigos; regeneração de `staticfiles/`; validação completa; checkpoint | suíte completa, lint, format, mypy, `makemigrations --check` |

As Fases D, E e F só são consideradas concluídas após a conferência visual em
todos os pontos de quebra da tabela de §5.5. Em nenhuma delas a conferência
começa pelo desktop.

## 7. Riscos

| Risco | Mitigação |
| --- | --- |
| Autorização regride ao expor cerca de vinte endpoints novos | Services já revalidam permissão (ADR-024); teste de `403` por endpoint |
| `must_change_password` deixa de ser imposto na SPA/API | Middleware devolve `403` tipado sob `/api/`, redireciona navegação direta para `/fe/senha` e possui teste dedicado |
| Sessão com CSRF exige origem única | Registrado na ADR-026; a criação futura de HML ou PRD reabre a ADR-014 |
| Contrato de erro divergente entre API e SPA | Envelope `{code, message, details}` fixado na Fase B, antes do Angular |
| `npm` como novo vetor de dependências | `package-lock.json` versionado, instalação por `npm ci`, Node 24.18.0 homologado |
| Perda da renderização sem JavaScript | O RNF-008 de `REQUIREMENTS.md` exige apenas os navegadores corporativos homologados |
| Atualização futura do Angular ou do PrimeNG | Versões fixadas no lockfile; atualização exige revisão técnica e de licenciamento explícita |
| Portar SCSS da referência reintroduz desktop first | Nenhuma consulta `max-width` é aceita em código novo; o SCSS da referência serve de fonte de tokens e não de layout |
| Telas administrativas densas são inviáveis em telefone | Cada listagem tem representação em cartões no estado base, definida em §5.5 e verificada nas Fases E e F |
| Regressão de responsividade a cada nova feature das Fases 3 a 6 | Pontos de quebra centralizados em `styles.scss` e conferência visual obrigatória no encerramento de cada fase |

Permanecem fora do escopo desta migração: Oracle, migrations, quota de 500 MB em
`PIMS_DATA`, contrato SQL do Senior, grants e políticas de auditoria de domínio.

## 8. Critérios de conclusão validados

A migração foi concluída com os seguintes critérios:

1. nenhum template server-side de aplicação existir, exceto os do Django Admin;
2. toda funcionalidade das catorze views removidas estiver acessível pela SPA;
3. cada endpoint novo possuir teste de permissão negada;
4. a senha temporária continuar sendo imposta, com teste;
5. a auditoria de login, logout, falha e manutenção de contas continuar sendo
   gerada, com teste;
6. `pytest`, `ruff check`, `ruff format --check`, `mypy`,
   `manage.py check` e `makemigrations --check` passarem;
7. `npm ci`, `ng build` e `ng test` passarem;
8. o smoke HTTP validar login, painel e telas funcionais, e o smoke somente
   leitura contra o Oracle DEV responder `200` nos quatro endpoints da cascata;
9. toda tela for utilizável a partir de 360 px de largura, sem rolagem
   horizontal no `body`, com alvos de toque de no mínimo 44 px e sem zoom
   automático ao focar campos no iOS;
10. nenhuma consulta `max-width` existir no SCSS da aplicação;
11. a documentação e o `CHECKPOINT.md` estiverem atualizados.
