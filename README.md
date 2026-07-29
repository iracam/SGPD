# SGPD / DesligaFlow

Sistema de Gestão do Processo Demissional.

O SGPD é um sistema corporativo para orquestrar o desligamento de colaboradores, desde a abertura pelo Departamento Pessoal até a liberação final para processamento da rescisão no Senior HCM.

O sistema não substitui o Senior HCM no cálculo ou processamento da rescisão. Seu papel é controlar, distribuir, registrar e auditar todas as validações necessárias entre DP, gestores e setores responsáveis.

## Objetivos principais

- Padronizar o processo demissional.
- Distribuir validações por setor.
- Controlar prazos e pendências.
- Registrar materiais, equipamentos, acessos, exames e documentos.
- Permitir evidências e rastreabilidade.
- Apoiar análise de valores sem executar descontos automaticamente.
- Integrar dados cadastrais do Senior HCM.
- Manter trilha de auditoria imutável.
- Liberar o processo ao DP somente quando os requisitos forem atendidos.

## Nome do projeto

- Nome institucional: `SGPD`
- Nome amigável: `DesligaFlow`

## Stack homologada na fundação

- Python 3.13
- Django 5.2 LTS
- Django REST Framework 3.17
- Angular 21 com PrimeNG 21, interface mobile first
- WhiteNoise para arquivos estáticos e para os assets da SPA
- Oracle Database 19c
- Celery ou Django-Q2 para tarefas assíncronas
- Redis em container quando filas, cache ou locks forem necessários
- cadastro de usuários e papéis funcionais no SGPD, com autenticação local e integração
  configurável com LDAP/Active Directory por `django-auth-ldap`
- Microsoft 365 SMTP para notificações
- filesystem local privado para evidências

As versões exatas do backend, inclusive dependências transitivas, estão
registradas em `uv.lock`; as do frontend, em `frontend/package-lock.json`.

A interface não depende de CDN: componentes, ícones e fontes são empacotados no
build.

A interface definitiva é uma SPA Angular, conforme as ADRs 025 a 028. O plano
concluído está registrado em `docs/SGPD/MIGRATION_FRONTEND_SPA.md`. O Django
Admin é a única interface server-side preservada.

## Execução local

Pré-requisitos: `uv`, Oracle Instant Client 19.28, cabeçalhos OpenLDAP/SASL e
um `.env` criado a partir de `.env.example`. No Debian:

```bash
sudo apt-get install build-essential ldap-utils libldap2-dev libsasl2-dev libssl-dev python3-dev
```

```bash
uv sync --dev
npm --prefix frontend ci
npm --prefix frontend run build
uv run manage.py check
uv run manage.py runserver
```

O Django serve a SPA construída: os assets saem pelo WhiteNoise na raiz e o
`index.html` por uma view dedicada, em origem única com a API.

Durante o desenvolvimento do frontend, com o Django rodando em `:8000`:

```bash
npm --prefix frontend start
```

`ng serve` sobe em `:4200` e encaminha `/api` e `/admin` ao Django pelo
`proxy.conf.json`, preservando a origem única exigida pela ADR-026.

Endpoints operacionais:

- `GET /health/live/`: processo Django ativo;
- `GET /health/ready/`: conexão Oracle disponível por `SELECT 1 FROM DUAL`.

Validações locais:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy apps config tests manage.py
uv run manage.py makemigrations --check --dry-run --settings=config.settings.test
npm --prefix frontend test
npm --prefix frontend run build
```

As migrations Oracle somente podem ser aplicadas após revisão do SQL. O
próprio usuário `SGPD` possui `CREATE TABLE` e `CREATE SEQUENCE`, ambos sem
`ADMIN OPTION`, e quota finita de 500 MB em `PIMS_DATA`. As migrations do
baseline e a remoção do campo LDAP legado foram aplicadas e validadas no DEV.
Migrations funcionais novas continuam exigindo revisão do SQL Oracle antes da
aplicação.

Não executar rollback para `zero` após existirem usuários ou auditoria: isso
removeria fisicamente o histórico. Correções de schema devem usar migration
adiante; recuperação operacional deve usar backup restaurado e procedimento
revisado.

Administração funcional de contas:

- `/fe/login`: autenticação local ou AD, conforme ativação e vínculo da conta;
- `/fe/usuarios`: criação e manutenção auditada de usuários;
- `DP` é o único papel funcional atribuível; `RESPONSAVEL_SETOR` é derivado do
  vínculo vigente mantido no cadastro do setor e pode coexistir na mesma conta;
- `/fe/auditoria`: auditoria de contas;
- `uv run manage.py bootstrap_roles`: reconciliação idempotente dos papéis
  funcionais fixos;
- `uv run manage.py bootstrap_identity_admin`: bootstrap interativo, único e
  auditado da primeira conta humana.
- `uv run manage.py check_active_directory`: valida configuração, transporte, bind e
  RootDSE sem listar dados pessoais.

Integração Active Directory:

- `/fe/configuracoes`: central técnica visível somente a SuperAdmin;
- `/fe/configuracoes/autenticacao`: configuração auditada de LDAP, upload e
  validação da CA, validação do contrato e teste de bind/RootDSE;
- `/fe/usuarios`: consulta usuários segundo os filtros salvos e cria conta
  local já vinculada;
- `/fe/usuarios/:id`: pesquisa e vincula uma identidade à conta existente;
- descoberta e autenticação possuem switches independentes;
- credenciais AD válidas nunca criam usuário ou permissão implicitamente;
- grupos AD podem restringir elegibilidade, mas o papel, associações de setor e
  escopos continuam no SGPD;
- a senha de bind salva pela interface fica cifrada e nunca é devolvida pela
  API; o certificado fica em storage privado fora do WhiteNoise;
- descoberta e login usam o mesmo transporte escolhido pelo SuperAdmin;
- com TLS, o SGPD monta LDAPS automaticamente e exige CA válida; sem TLS,
  funciona com aviso permanente de que a credencial técnica e as senhas dos
  usuários trafegam sem criptografia;
- o login AD só pode ser ativado depois de teste bem-sucedido da mesma
  configuração e contingência local de SuperAdmin;
- configuração e filtros estão em
  `docs/SGPD/INTEGRATION_ACTIVE_DIRECTORY.md`.

Configuração funcional:

- `/fe/setores`: cadastro auditado de setores, escopos e múltiplos
  responsáveis;
- `/fe/workflow-config`: cadastro e publicação auditada de templates,
  perguntas e grupos versionados;
- escopos globais, por empresa ou por filial, usando somente os códigos do
  Senior e sem replicar referências;
- prazos, bloqueio, valores, evidência e destino de escalada configuráveis;
- setores são inativados, nunca excluídos;
- responsáveis possuem a mesma autoridade, validade explícita, escopo herdado
  do setor e revogação lógica, sem coordenador ou substituto.

Processo demissional:

- `/fe/colaboradores`: seleção Empresa → Filial → Tipo de colaborador
  → Colaborador e abertura do rascunho;
- exige uma atribuição `DP` explícita, ativa, vigente e compatível com empresa
  e filial; SuperAdmin e responsabilidade pelo setor Departamento Pessoal não
  substituem o papel;
- o service consulta novamente o Senior somente por `SELECT`, grava processo,
  snapshot imutável e evento `PROCESS_OPENED` na mesma transação;
- duplicidade de processo não encerrado para a mesma chave do colaborador é
  impedida por validação e unicidade no Oracle.
- `/fe/processos/:uuid/rascunho`: seleção explícita de grupos, prévia dos
  setores e bloqueios e início idempotente;
- o início não relê o Senior, revalida `DP`, escopo, estado e responsáveis
  vigentes, gera uma tarefa por setor e congela template e perguntas;
- a ausência de responsável vigente em setor obrigatório bloqueia toda a
  transação, sem criar tarefa, auditoria parcial ou chave idempotente.
- `/fe/tarefas`: responsáveis vigentes veem somente tarefas dos próprios
  setores no escopo do processo, iniciam a análise e concluem o checklist;
- início e conclusão da tarefa usam versão otimista, lock, `Idempotency-Key`,
  auditoria e rollback atômico; itens que exigem arquivo ou evidência aguardam
  a Fase 5.

## Escopo técnico atual

- somente ambiente DEV;
- sem Nginx;
- sem CI/CD;
- WhiteNoise não atende evidências ou uploads;
- Redis e worker serão introduzidos sob demanda;
- aplicação e API permanecem na mesma origem, exigência da ADR-026.

A SPA vive em `frontend/`. As versões exatas estão em
`frontend/package-lock.json`; a instalação é sempre por `npm ci`.

## Estrutura da documentação (`./docs/SGPD/`)

- `VISION.md`: visão do produto.
- `ENVIRONMENT.md`: inventário e matriz dos ambientes.
- `REQUIREMENTS.md`: requisitos funcionais e não funcionais.
- `WORKFLOWS.md`: fluxo e estados do processo.
- `DATA_MODEL.md`: modelo conceitual de referência e estado de implementação.
- `ARCHITECTURE.md`: arquitetura da solução.
- `INTEGRATION_SENIOR_ORACLE.md`: integração com Senior HCM e Oracle.
- `INTEGRATION_ACTIVE_DIRECTORY.md`: descoberta, vínculo e autenticação AD.
- `SECURITY.md`: segurança, LGPD e auditoria.
- `RISK_REGISTER.md`: registro e mitigação de riscos.
- `DECISIONS.md`: decisões arquiteturais vigentes e índice das substituídas.
- `MIGRATION_FRONTEND_SPA.md`: registro do plano executado de migração para a SPA.
- `ROADMAP.md`: fases de implementação.
- `CHECKPOINT.md`: controle de progresso do projeto.

## Na raiz do projeto

- `AGENTS.md`: instruções para agentes de IA.
- `PROMPT.md`: prompt principal para o Codex.

## Princípios do projeto

1. O Senior HCM permanece como sistema oficial do vínculo e da rescisão.
2. O SGPD é o orquestrador do processo.
3. Nenhuma escrita direta será feita em tabelas internas do Senior.
4. O banco Oracle do SGPD terá owner exclusivo.
5. No DEV, por decisão explícita, o owner `SGPD` será também o usuário da aplicação; não será criado `SGPD_APP`.
6. Referências do Senior serão consultadas em tempo real por SQL `SELECT` parametrizado, sem models ou cópias `REF_*` no SGPD.
7. Dados do colaborador serão copiados para um snapshot na abertura do processo.
8. Regras e checklists serão versionados.
9. Pendências serão entidades próprias e auditáveis.
10. Valores informados serão tratados como pretensões de cobrança.
11. A abertura, análise final, liberação e encerramento continuarão sob
    responsabilidade de usuário com o papel `DP` vigente no escopo do processo.

## Estado atual

A descoberta do ambiente e o contrato SQL do Senior estão concluídos. A
fundação Django está criada e validada localmente; a aplicação conecta ao
Oracle com `python-oracledb` em modo Thick. A base de autenticação, usuários,
papéis funcionais, escopos, vínculo administrativo com o AD e auditoria foi
aplicada no Oracle DEV. O catálogo atribuível contém somente `DP`;
`RESPONSAVEL_SETOR` é derivado dos vínculos de setor e os papéis legados
permanecem inativos sem apagar histórico.
A descoberta LDAP, a importação/vinculação verificada e o backend
de autenticação foram implementados com Django 5.2.16 LTS,
`django-auth-ldap` 5.3.0 e `python-ldap` 3.4.7. Bind, bases e grupo foram
validados. O transporte de descoberta e login é uma escolha única: TLS monta
LDAPS automaticamente; LDAP simples permanece operacional com aviso explícito
de exposição das credenciais. O login AD permanece desligado até concluir um
teste controlado da configuração escolhida.
A primeira conta humana foi criada explicitamente pelo bootstrap auditado;
nenhuma conta é criada automaticamente pelo login AD.

A seleção cadastral da Fase 2 está concluída e usa o mesmo repository e a
mesma autorização por escopo dos endpoints JSON. O `LEFT JOIN` de centro de
custo foi homologado no Oracle DEV e a consulta de colaboradores concluiu a
medição controlada com até dez conexões concorrentes sem erros ou timeouts.

A Fase 4 possui abertura, início e ciclo inicial das tarefas implementados. A SPA permite ao
`DP` selecionar colaborador e gestor, informar datas, motivo, prioridade e
observações e criar o processo em `RASCUNHO`. O backend revalida
`has_effective_role()` após bloquear a autoridade funcional, relê a chave
completa no Senior, preserva os snapshots do colaborador e do gestor e registra
auditoria append-only. Templates e grupos possuem versões publicadas imutáveis;
um mesmo template pode ser associado a diferentes setores nos grupos. O
rascunho fixa as versões escolhidas e o início idempotente gera tarefas e
snapshots de perguntas em `INICIADO`. Responsáveis vigentes podem movimentar
as tarefas `PENDENTE → EM_ANALISE → CONCLUIDA` e responder os tipos simples do
checklist pela SPA; respostas de arquivo ou com evidência obrigatória
permanecem bloqueadas até a Fase 5. As migrations `templates_engine.0001`,
`templates_engine.0002` e `offboarding.0002` foram aplicadas e validadas no
Oracle DEV. Entidades configuráveis locais usam código numérico automático
igual ao `ID`: setores, templates, grupos e perguntas não solicitam código do
usuário. Elas são localizadas funcionalmente pelo nome ou texto da pergunta;
o número serve como referência estável. Códigos oficiais do Senior e códigos
funcionais fixos não pertencem a essa regra. Templates e grupos permitem editar
somente a versão em rascunho, com concorrência otimista e auditoria; conteúdo
publicado exige uma nova versão. A migration `templates_engine.0003` foi
aplicada e validada no Oracle DEV.

SMTP AUTH e o uso do remetente configurado foram validados no Microsoft 365
via TLS/STARTTLS em 2026-07-28. Uma mensagem de prova foi aceita pelo serviço.

O checkpoint das Fases 1 e 2 foi estabilizado e versionado localmente em
2026-07-28. Os services administrativos validam a permissão do ator, a
auditoria rejeita mutação e exclusão em lote, e a desativação concorrente
preserva ao menos um superusuário ativo. A Fase 3 foi iniciada pelo cadastro
de setores, seus escopos e responsáveis. O Oracle DEV contém os nove setores
informados pelo responsável funcional, ainda com prazo, escopo e regras
provisórios. O cadastro de responsáveis está implementado e o Oracle DEV
contém 10 associações ativas cobrindo os nove setores. Grupos, regras e
templates agora são configuráveis, sem carga funcional automática. O Oracle
DEV contém o template piloto `Demissional Geral` e o grupo piloto `Todos`
publicados; seu conteúdo, SLAs e composição ainda precisam de homologação
funcional antes de uso operacional. Templates são neutros quanto a setor. O
papel `DP` possui uma atribuição global ativa para `victor.delgado`; qualquer capacidade
`RESPONSAVEL_SETOR` é derivada de seus vínculos vigentes.

A migração da interface foi concluída. A API de autenticação, contexto,
administração de contas e workflow está publicada em `/api/v1/`, e a SPA
autentica, aplica o tema, filtra o menu pelo contexto do servidor, administra
contas, configura grupos/templates, abre e inicia o rascunho. O Django Admin somente leitura
permanece como ferramenta técnica de diagnóstico.

Em 2026-07-29, um smoke transacional no Oracle DEV validou o fluxo
abrir → selecionar → iniciar com os services reais: nove tarefas, nove
snapshots de checklist, três eventos de auditoria e replay idempotente foram
confirmados. O rollback obrigatório removeu integralmente processo, snapshot,
tarefas, itens, auditoria e chave de idempotência criados pelo teste. Um
segundo smoke validou início e conclusão de uma tarefa, inclusive retries
idempotentes, e também foi integralmente revertido. O Senior foi acessado
somente por `SELECT`.

Consulte `PROMPT.md` para o procedimento completo.
