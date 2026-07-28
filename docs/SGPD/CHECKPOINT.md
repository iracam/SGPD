# Checkpoint do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Fase atual: Fases 1 e 2 estabilizadas; Fase 2.5 em execução na etapa A; Fase 3 ainda não iniciada
- Estado: Decisões da migração de frontend registradas; nenhum código alterado por elas
- Banco: Oracle
- Backend: Django, evoluindo para API-only
- UI: SPA Angular 21 + PrimeNG 21, mobile first, decidida nas ADR-025 a ADR-028; interface Django Templates + HTMX + Alpine ainda em operação até a Fase G
- Integração principal: Senior HCM
- Autenticação: local no MVP, por sessão Django com CSRF em origem única, com vinculação futura das contas SGPD ao Active Directory

## Checkpoint 0 — Descoberta

### Ambiente

- [x] Confirmar sistema operacional do DEV: Debian 13.6, kernel 6.12, x86_64.
- [x] Confirmar versão do Python no ambiente local: CPython 3.13.5.
  - Python 3.13 homologado no `pyproject.toml`.
- [x] Confirmar versão do Oracle Database: Oracle 19c.
- [x] Confirmar driver Oracle disponível.
  - Oracle Instant Client 19.28 em `/opt/oracle/instantclient_19_28`.
  - SQLcl local 26.1 disponível; conexão Oracle do `.env` validada.
  - `python-oracledb` 4.0.2 instalado e validado em modo Thick.
- [x] Confirmar escopo de ambientes: somente DEV; HML e PRD fora do escopo atual.
- [x] Confirmar padrão de secrets do DEV.
  - Usuário, senha e e-mail no `.env`; usuários individuais seguem `nome.sobrenome`.
- [x] Confirmar SMTP.
  - Microsoft 365 em `smtp.office365.com:587` com TLS/STARTTLS.
  - Remetente `noreply@bsabioenergia.com.br`; credenciais e e-mail no `.env`.
- [x] Confirmar estratégia de Redis.
  - Servidor não ficará ativo agora; será iniciado em container quando necessário.
- [x] Confirmar storage de evidências.
  - Filesystem local privado, inicialmente em `media/evidence`, fora do WhiteNoise.
- [x] Confirmar entrega de arquivos estáticos.
  - Sem Nginx; usar WhiteNoise exclusivamente para arquivos estáticos.
- [x] Confirmar CI/CD.
  - Não será utilizado no escopo DEV atual; validações serão locais.

### Senior HCM

- [x] Confirmar owner.
  - Schema de origem `VETORH`.
- [x] Confirmar objetos e grants disponíveis.
  - `SGPD` possui `SELECT` direto em `R034FUN`, `R010SIT`, `R030FIL`, `R024CAR` e `R018CCU`.
- [x] Definir estratégia de acesso.
  - Consulta online por SQL parametrizado, sem models Senior, views Oracle locais, tabelas `REF_*` ou sincronização.
- [x] Mapear empresa.
- [x] Mapear filial.
- [x] Mapear tipo de colaborador.
- [x] Mapear colaborador.
- [x] Mapear cargo.
- [x] Retirar local do contrato e das regras do MVP.
- [x] Mapear centro de custo.
- [x] Retirar gestor da integração Senior.
  - Gestores serão usuários cadastrados no SGPD.
- [x] Retirar e-mail da integração Senior.
  - E-mails serão mantidos no cadastro local de usuários.
- [x] Confirmar data de atualização.
  - `VETORH.R034FUN.USU_DATALT`, tipo Oracle `DATE`, anulável.
- [x] Confirmar tratamento da data de afastamento.
  - `DATAFA` nula ou igual a `DATE '1900-12-31'` retorna `NULL`; demais valores permanecem `DATE`.
- [x] Confirmar regras de colaborador ativo.
  - Regra homologada: `SITAFA <> 7`, isto é, qualquer situação diferente de “Demitido”.
  - `R010SIT` confirmou 1 = Trabalhando, 2 = Férias e 7 = Demitido.
- [ ] Definir estratégia de homologação.
- [x] Definir usuário Oracle do runtime.
  - Por decisão explícita no DEV, usar o owner `SGPD`; não criar `SGPD_APP`.

### Processo funcional

- [ ] Validar fluxo atual.
- [ ] Identificar setores.
- [ ] Identificar responsáveis.
- [ ] Levantar checklists atuais.
- [ ] Levantar prazos.
- [ ] Levantar regras de bloqueio.
- [ ] Levantar evidências.
- [ ] Levantar valores.
- [ ] Levantar aprovações.
- [ ] Levantar exceções.
- [ ] Validar cancelamento.
- [ ] Validar reabertura.
- [ ] Validar encerramento.

### Segurança

- [x] Retirar grupos AD como fonte de papéis.
  - Papéis e escopos serão mantidos exclusivamente no SGPD.
- [x] Implementar fluxo administrativo de vínculo e desvínculo AD.
  - Identificador opaco, único e normalizado; confirmação, justificativa,
    responsável e auditoria.
- [ ] Homologar atributo identificador, endpoint, TLS, base de busca e backend
  de autenticação com a Infraestrutura.
- [x] Definir origem dos usuários.
  - Todos os usuários, gestores e e-mails serão cadastrados no SGPD.
  - AD será vinculado futuramente apenas como provedor de autenticação.
- [x] Definir papéis.
  - Catálogo inicial com nove papéis; permissões evoluem com os módulos.
- [x] Definir escopo por empresa/filial.
  - Global, empresa e filial, com validade e revogação lógica.
- [ ] Definir dados sensíveis.
  - Postergado por decisão do projeto em 2026-07-28.
- [ ] Definir retenção.
  - Postergado por decisão do projeto em 2026-07-28.
- [ ] Definir acesso a documentos médicos.
- [ ] Definir acesso a valores.
- [ ] Definir política ampla de auditoria.
  - Postergada por decisão do projeto em 2026-07-28; a auditoria técnica de
    contas já implementada permanece ativa.

### Arquitetura

- [x] Criar ADRs iniciais.
- [x] Validar módulos Django.
- [x] Definir estrutura de settings.
- [ ] Definir filas.
- [ ] Definir storage.
- [x] Definir logging.
- [x] Definir health checks.
- [ ] Definir backups.
- [ ] Definir observabilidade.

## Checkpoint 1 — Fundação técnica

- [x] Repositório criado.
- [x] `pyproject.toml` criado.
- [x] Django iniciado.
- [x] Settings do DEV.
- [x] `.env.example`.
- [x] Oracle conectado.
  - Modo Thick obrigatório para o verificador atual da conta `SGPD`.
  - `CREATE TABLE` e `CREATE SEQUENCE`, ambos sem `ADMIN OPTION`, e quota de
    500 MB em `PIMS_DATA` concedidos ao mesmo usuário `SGPD`.
  - 23 migrations aplicadas; 12 constraints SGPD habilitados e validados.
- [x] Cadastro e manutenção auditada de usuários.
- [x] Autenticação local e troca obrigatória de senha temporária.
- [x] Papéis, permissões e escopos.
- [x] Vínculo administrativo com o AD.
- [x] Auditoria de login, logout, falha e manutenção de contas.
- [x] Primeira conta humana de administração.
  - Criada pelo bootstrap interativo, com papel global
    `ADMIN_IDENTIDADE` e dois eventos de auditoria.
- [x] SMTP AUTH e `Send As`.
  - Após atualização das credenciais em 2026-07-28, o Microsoft 365 aceitou
    uma mensagem de prova enviada ao próprio remetente configurado.
- [ ] Redis conectado, quando requerido.
- [ ] Worker conectado, quando requerido.
- [x] Health check.
- [x] Logging estruturado.
- [x] Testes executando.
- [x] Lint e format.
- [x] CI/CD não aplicável ao escopo atual.

## Checkpoint 2 — Integração cadastral

- [x] Estratégia sem models `REF_*` definida.
- [x] Objetos Senior e grants iniciais validados.
- [x] Contrato SQL parametrizado versionado.
- [x] Repository Django sem models.
- [x] Paginação, limites e timeout inicial definidos.
- [x] Tratamento de indisponibilidade.
- [x] Logs de consulta e telemetria básica de duração/linhas.
- [x] Script SQLcl de teste de contrato.
- [x] Cascata funcionando no repository, endpoints autenticados e interface
  HTMX.
  - Runtime HTMX 2.0.10 servido localmente, sem CDN.
- [x] Autorização da cascata por permissão, empresa e filial.
- [x] `LEFT JOIN` de centro de custo homologado.
  - Em 2026-07-28, preservou 1.891 elegíveis; `INNER JOIN` excluiria os 49
    colaboradores sem referência em `R018CCU`; nenhuma chave de centro de
    custo duplicada foi encontrada.
- [x] Concorrência inicial medida no DEV.
  - 80 consultas de colaboradores com 1, 5 e 10 conexões, sem erros ou
    timeouts; p95 máximo de 60,64 ms.
- [ ] Snapshot validado.

## Checkpoint 2.5 — Migração da interface para SPA Angular

Plano completo em `MIGRATION_FRONTEND_SPA.md`.

### Fase A — Decisão e documentação

- [x] ADR-025: SPA Angular substitui a interface server-side.
- [x] ADR-026: sessão Django com CSRF em origem única; sem JWT.
- [x] ADR-027: PrimeNG e build integrado ao WhiteNoise.
- [x] ADR-028: mobile first como requisito de interface.
- [x] ADR-002 marcada como substituída.
- [x] Proibição de SPA removida do `AGENTS.md` e substituída pela proibição de
  novas telas server-side.
- [x] Stack, estrutura e papéis de agente atualizados no `AGENTS.md`.
- [x] `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `ENVIRONMENT.md`,
  `ROADMAP.md`, `INTEGRATION_SENIOR_ORACLE.md` e `PROMPT.md` atualizados.
- [x] Riscos R38 a R43 registrados; R34 encerrado.
- [x] Node 24.18.0 e npm 11.16.0 homologados.
- [x] `MANIFEST.json` atualizado.

### Fase B — API de autenticação e contexto

- [x] Envelope de erro `{code, message, details}` e handler único do DRF.
  - Endpoints cadastrais do Senior alinhados ao mesmo envelope.
  - Ausência de sessão passa a responder `401`, e não o `403` do DRF.
- [x] `GET /api/v1/auth/csrf/`.
- [x] `POST /api/v1/auth/login/` com auditoria e limitação de tentativas.
  - CSRF validado explicitamente, pois o DRF não o exige em `POST` anônimo.
- [x] `POST /api/v1/auth/logout/` com auditoria.
- [x] `GET /api/v1/auth/me/` com `must_change_password`.
- [x] `GET /api/v1/auth/context/` com papéis, permissões e escopos.
- [x] `POST /api/v1/auth/change-password/`.
- [x] Middleware devolvendo `403` tipado sob `/api/`.

### Fase C — API de contas

- [x] Usuários: listagem com busca, criação, detalhe e atualização.
- [x] Redefinição de senha.
- [x] Papéis: listagem, criação, detalhe e atualização.
- [x] Atribuição e revogação de papéis.
- [x] Vínculo e desvínculo AD.
- [x] Catálogo de permissões delegáveis.
- [x] Auditoria de contas paginada, com filtro por usuário e tipo de evento.
- [x] Teste de permissão negada em cada endpoint.
  - Anônimo e autenticado sem permissão, para os 15 pares de rota e método.
  - R38 mitigado.

### Fase D — Scaffold Angular, shell e autenticação

- [x] `frontend/` com Angular 21, PrimeNG 21 e Aura.
- [x] Tokens do SGPD e pontos de quebra em `styles.scss`.
  - Grafite `#232733` e verdigris `#4fb3a5`; raiz 16 px no base e 14 px a
    partir de `lg`.
- [x] `core/auth`, `core/config`, `core/layout` e `core/theme`.
- [x] Shell com gaveta móvel promovida a barra lateral a partir de 1024 px.
- [x] Tela de login.
- [x] Tela de troca da própria senha, exigida pelo fluxo de senha temporária.
- [x] Painel inicial com sessão, papéis e escopos.
- [x] Integração do build com Django e WhiteNoise.
- [x] Testes de frontend com Vitest.
- [x] Conferência visual em 360, 390, 768, 1024 e 1440 px.
  - Executada em Chromium 150 com sessão real, contra SQLite efêmero.
  - 67 verificações automatizadas sem falha; seis defeitos corrigidos.
- [x] PrimeNG fixado na 21, última versão MIT.

### Fase E — Telas de contas

- [ ] Usuários, com cartões no estado base e tabela a partir de `md`.
- [ ] Papéis.
- [ ] Auditoria.
- [ ] Perfil e troca da própria senha.
- [ ] Conferência visual nos cinco pontos de quebra.

### Fase F — Cascata Senior

- [ ] Seleção Empresa → Filial → Tipo → Colaborador na SPA.
- [ ] Smoke somente leitura contra o Oracle DEV.
- [ ] Conferência visual nos cinco pontos de quebra.

### Fase G — Remoção e limpeza

- [ ] Templates, views HTML, forms e context processors removidos.
- [ ] `ui_urls` e runtime HTMX removidos.
- [ ] `staticfiles/` regenerado.
- [ ] Testes acoplados à UI antiga removidos.
- [ ] Suíte completa, lint, format, mypy e migrations sem divergência.
- [ ] Checkpoint atualizado.

## Checkpoint 3 — Configuração funcional

- [ ] Setores.
- [ ] Responsáveis.
- [ ] Grupos.
- [ ] Regras.
- [ ] Templates.
- [ ] Versionamento.
- [x] Permissões.
  - Infraestrutura de papéis e escopos concluída; novas permissões serão
    adicionadas conforme cada módulo funcional.

## Checkpoint 4 — Workflow

- [ ] Abertura.
- [ ] Início.
- [ ] Tarefas.
- [ ] Estados.
- [ ] Prazos.
- [ ] Painéis.
- [ ] Auditoria.

## Checkpoint 5 — Pendências

- [ ] Cadastro.
- [ ] Ciclo de vida.
- [ ] Evidências.
- [ ] Hash.
- [ ] Bloqueios.
- [ ] Regularização.
- [ ] Decisões.

## Checkpoint 6 — Liberação

- [ ] Prontidão automática.
- [ ] Revisão do DP.
- [ ] Liberação.
- [ ] Registro de rescisão.
- [ ] Encerramento.
- [ ] Cancelamento.
- [ ] Reabertura.

## Registro de decisões

Use esta seção em cada execução:

```text
Data:
Responsável:
Fase:
O que foi concluído:
Decisões:
Riscos:
Pendências:
Próximo passo:
Comandos executados:
Arquivos alterados:
Testes:
```

### 2026-07-27 — Inicialização do repositório

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação
O que foi concluído: estrutura e integridade documental validadas; repositório Git e remoto confirmados; .gitignore preparado para a stack planejada.
Decisões: manter o escopo desta execução na preparação do repositório, sem iniciar o scaffold Django antes do levantamento do ambiente.
Riscos: Python local 3.13.5 ainda não homologado para o projeto; versões e serviços da stack permanecem indefinidos.
Pendências: levantamento de ambiente, .env.example, pyproject.toml, scaffold Django, testes e CI.
Próximo passo: executar o levantamento do ambiente e definir as versões homologadas da fundação.
Comandos executados: inspeção da árvore e do Git; validação JSON e SHA-256 do manifesto; teste das regras do .gitignore; git diff --check.
Arquivos alterados: .gitignore, AGENTS.md, README.md, docs/SGPD/CHECKPOINT.md e docs/SGPD/MANIFEST.json.
Testes: manifesto íntegro; padrões do .gitignore verificados; diff sem erros de whitespace.
```

### 2026-07-27 — Descoberta do ambiente

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Ambiente
O que foi concluído: inventário local de SO, runtimes, ferramentas, Oracle Client, Docker, serviços, filesystem e configurações do repositório.
Decisões: separar fatos do ambiente local das confirmações ainda necessárias para DEV/HML/PRD; manter variáveis preliminares e sem segredos.
Riscos: Python ainda não homologado; serviços e ambientes corporativos indefinidos; toolchain global divergente.
Pendências: Oracle Database e driver; DEV/HML/PRD; secrets; SMTP; Redis; storage; Nginx; CI/CD; LDAP/AD.
Próximo passo: obter da Infraestrutura a matriz dos ambientes e homologar Python, Oracle e o padrão de secrets.
Comandos executados: inventário de SO e runtimes; inspeção de pacotes; estado do Docker e serviços; teste local de Redis; inspeção de disco e configurações.
Arquivos alterados: .env.example, README.md, docs/SGPD/ENVIRONMENT.md, docs/SGPD/RISK_REGISTER.md, docs/SGPD/CHECKPOINT.md e docs/SGPD/MANIFEST.json.
Testes: nenhum segredo exposto; serviços consultados somente em leitura; documentação e manifesto validados.
```

### 2026-07-27 — Consolidação do ambiente DEV

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Ambiente
O que foi concluído: escopo limitado ao DEV; WhiteNoise definido para estáticos; Nginx e CI/CD removidos do escopo; Redis definido como container sob demanda.
Decisões: WhiteNoise não servirá evidências ou uploads; Redis e worker somente serão introduzidos quando houver dependência funcional.
Riscos: execução sem CI/CD exige comandos locais reproduzíveis; storage de evidências permanece indefinido.
Pendências: homologar Python; configurar Oracle; definir secrets, SMTP, LDAP/AD e storage de evidências.
Próximo passo: homologar Python e preparar a fundação Django do DEV.
Comandos executados: revisão cruzada da documentação, arquitetura, roadmap, riscos e contrato de variáveis.
Arquivos alterados: .env.example, README.md e documentação em docs/SGPD.
Testes: consistência documental, manifesto, JSON, variáveis sem segredos e diff validados.
```

### 2026-07-27 — Confirmação do Oracle DEV

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Ambiente
O que foi concluído: Oracle Database 19c, Instant Client 19.28 e MCP Oracle SQLcl confirmados.
Decisões: usar o cliente em /opt/oracle/instantclient_19_28; instalar python-oracledb durante a fundação.
Riscos: conexão SGPD, grants, modo Thin/Thick e acesso somente leitura do Senior ainda precisam ser validados.
Pendências: conectar de forma controlada ao DEV e confirmar usuário, privilégios, DSNs, TLS e catálogo.
Próximo passo: executar o bloco Senior HCM com consultas estritamente read-only.
Comandos executados: inspeção do cliente local e listagem não destrutiva das conexões salvas no MCP Oracle.
Arquivos alterados: .env.example, README.md e documentação em docs/SGPD.
Testes: MCP disponível; conexão DEV listada; nenhum SQL executado.
```

### 2026-07-27 — Conclusão do ambiente DEV

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Ambiente
O que foi concluído: padrão de secrets, SMTP Microsoft 365 e storage local de evidências definidos.
Decisões: credenciais no .env; usuários individuais no padrão nome.sobrenome; evidências em filesystem privado; WhiteNoise restrito a estáticos.
Riscos: SMTP AUTH e Send As ainda precisam ser testados.
Pendências: nenhuma no inventário Ambiente; instalações e testes seguem para a fundação técnica.
Próximo passo: iniciar o levantamento do Senior HCM ou homologar a fundação Django.
Comandos executados: confirmação oficial dos parâmetros SMTP e revisão cruzada da documentação.
Arquivos alterados: .env.example, README.md e documentação em docs/SGPD.
Testes: variáveis sem segredos; consistência documental; manifesto e links validados.
```

### 2026-07-27 — Descoberta do acesso direto ao Senior HCM

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Senior HCM
O que foi concluído: owner SGPD do DEV conectado; Oracle 19.15 confirmado; schema VETORH identificado; grants SELECT e consulta de colaboradores validados sem expor dados pessoais.
Decisões: consultar VETORH diretamente por SQL parametrizado na camada repository/service; não criar models Senior, views Oracle locais, tabelas REF_*, cargas ou sincronização; persistir somente o snapshot da abertura.
Riscos: owner SGPD ainda está no .env e não pode ser usuário de runtime; acesso direto acopla o SGPD ao contrato físico do Senior; CPF, performance, disponibilidade e joins internos exigem controles. [Separação do owner superada posteriormente pela ADR-022.]
Pendências: criar SGPD_APP com grants mínimos; decidir necessidade de local; mapear gestor e fonte do e-mail; homologar DATAFA sentinela e INNER JOIN; medir consultas e definir timeout/paginação. [SGPD_APP, local, gestor e e-mail resolvidos por decisões posteriores.]
Próximo passo: criar o usuário operacional e fechar o contrato SQL do fluxo Empresa → Filial → Tipo → Colaborador. [Criação do usuário superada posteriormente pela ADR-022.]
Comandos executados: inspeção segura do .env; conexão SQLcl; consultas a metadados de sessão, versão, grants e objetos; probe limitado da consulta fornecida; chmod 600 no .env.
Arquivos alterados: .env.example, README.md e documentação em docs/SGPD.
Testes: conexão SGPD bem-sucedida; cinco grants SELECT diretos confirmados; cinco objetos VETORH válidos; probe da consulta retornou uma linha; nenhum DML ou DDL executado.
```

### 2026-07-27 — Homologação da situação funcional

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Senior HCM
O que foi concluído: catálogo completo de situações consultado em R010SIT com o usuário VETORH; códigos 1, 2 e 7 confirmados.
Decisões: colaborador elegível é aquele com SITAFA <> 7; para o SGPD, ativo significa não demitido, inclusive quando houver outro afastamento.
Riscos: a regra inclui todos os afastamentos diferentes de 7 e deverá permanecer explícita para não ser reduzida indevidamente aos códigos 1 e 2.
Pendências: decidir necessidade de local no MVP; mapear gestor; definir Senior ou AD/LDAP como fonte do e-mail.
Próximo passo: fechar os atributos do contrato e criar SGPD_APP com os grants mínimos. [Criação do usuário superada posteriormente pela ADR-022.]
Comandos executados: SELECT * FROM R010SIT ORDER BY CODSIT com o usuário VETORH.
Arquivos alterados: docs/SGPD/REQUIREMENTS.md, docs/SGPD/INTEGRATION_SENIOR_ORACLE.md, docs/SGPD/CHECKPOINT.md e docs/SGPD/MANIFEST.json.
Testes: consulta somente leitura concluída; 1 = Trabalhando, 2 = Férias e 7 = Demitido confirmados; nenhum DML ou DDL executado.
```

### 2026-07-27 — Fronteira de usuários e identidade

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Identidade
O que foi concluído: local retirado do MVP; gestor e e-mail retirados do contrato Senior; origem cadastral dos usuários definida.
Decisões: todos os usuários, gestores, e-mails, papéis e escopos serão cadastrados no SGPD; autenticação local no MVP; vinculação futura ao AD somente para autenticação com uma única senha.
Riscos: vínculo AD incorreto ou duplicado; manutenção indevida de senha local após a vinculação; alteração de gestor ou e-mail afetar histórico se não houver snapshot.
Pendências: definir papéis, política de senha local, identificador corporativo imutável, fluxo de vinculação ao AD e contas de contingência.
Próximo passo: detalhar cadastro de usuários e papéis da fundação técnica.
Comandos executados: revisão cruzada de requisitos, arquitetura, dados, integração, segurança, roadmap e checkpoint.
Arquivos alterados: README.md e documentação em docs/SGPD.
Testes: consistência documental, manifesto e diff validados; nenhum model, migration ou código criado.
```

### 2026-07-27 — Data de atualização do colaborador

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Senior HCM
O que foi concluído: R034FUN.USU_DATALT confirmada como data de atualização da origem.
Decisões: retornar USU_DATALT como DATE anulável e preservá-la no snapshot; não usar o campo para sincronização, pois a consulta ao Senior é online.
Riscos: registros podem possuir USU_DATALT nula; a aplicação não deve interpretar nulo como ausência ou invalidade do colaborador.
Pendências: incluir o campo no contrato SQL implementado e nos testes de integração.
Próximo passo: concluir as pendências restantes do contrato Senior.
Comandos executados: consulta a ALL_TAB_COLUMNS e probe não nulo em VETORH.R034FUN, usando SGPD.
Arquivos alterados: docs/SGPD/REQUIREMENTS.md, docs/SGPD/DATA_MODEL.md, docs/SGPD/INTEGRATION_SENIOR_ORACLE.md, docs/SGPD/CHECKPOINT.md e docs/SGPD/MANIFEST.json.
Testes: coluna USU_DATALT confirmada como DATE, armazenamento de 7 bytes, anulável e com ao menos um valor não nulo; nenhum DML ou DDL executado.
```

### 2026-07-27 — Contrato SQL e decisão do usuário Oracle

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Senior HCM
O que foi concluído: SGPD_APP descartado por decisão explícita; owner SGPD definido como conexão única DEV; cinco consultas parametrizadas versionadas e validadas.
Decisões: usar SGPD para runtime e migrations; não criar outro usuário Oracle; LEFT JOIN em R018CCU para não ocultar colaboradores; paginação máxima 100 e timeout inicial de 5 segundos.
Riscos: owner no runtime amplia impacto de falha; 49 de 1.889 colaboradores elegíveis não possuem referência em R018CCU; desempenho sob concorrência ainda não medido.
Pendências: implementar repository Django sem models; homologar centro de custo ausente; tratar indisponibilidade; adicionar logs, métricas e testes automatizados após a fundação.
Próximo passo: iniciar a fundação técnica e implementar o repository que consome o contrato SQL.
Comandos executados: inspeção de privilégios de SGPD; consultas de metadados; contagem global de integridade; execução repetida do script SQLcl read-only; validação do wrapper local.
Arquivos alterados: AGENTS.md, .env.example, README.md, documentação em docs/SGPD e scripts/oracle/validate_senior_reference_queries.sql.
Testes: empresas=7, filiais probe=1, tipos probe=1, colaboradores probe=5, detalhe=1; consultas paginadas/detalhe em até 42 ms na execução final; USU_DATALT DATE anulável; DATAFA sentinela em 1.815 de 1.889 elegíveis; nenhum DML ou DDL executado.
```

### 2026-07-27 — Fundação Django e conexão Oracle

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 0 — Descoberta e fundação / Fundação técnica
O que foi concluído: Python 3.13 e Django 5.2 LTS homologados; dependências bloqueadas com uv; projeto Django, settings, usuário local extensível para AD, WhiteNoise, logs JSON, correlation ID e health checks implementados.
Decisões: usar python-oracledb Thick com Instant Client 19.28 porque o modo Thin não suporta o verificador atual de SGPD; usar SQLite em memória apenas nos testes unitários; manter SGPD como única conta Oracle conforme ADR-022.
Riscos: SGPD não possui privilégio de sistema nem quota, portanto as migrations não podem ser aplicadas; o modo Thick torna o Instant Client obrigatório; autenticação e autorização funcionais ainda não foram implementadas.
Pendências: DBA conceder CREATE TABLE e quota no tablespace designado ao próprio SGPD; aplicar e validar migrations após revisão; implementar repository Senior sem models.
Próximo passo: implementar e testar o repository de leitura do contrato Senior, sem depender de migrations.
Comandos executados: uv sync; ruff; mypy; pytest; manage.py check; makemigrations --check; sqlmigrate; SELECT 1 FROM DUAL; health/ready; consultas read-only a USER_SYS_PRIVS e USER_TS_QUOTAS.
Arquivos alterados: pyproject.toml, uv.lock, manage.py, apps/accounts, apps/core, config, tests, .env.example, README.md e documentação em docs/SGPD.
Testes: 7 testes passaram; ruff, format, mypy e Django check sem erros; migration sem divergências; SQL Oracle revisado sem aplicação; readiness DEV respondeu 200; nenhum DDL ou DML executado.
```

### 2026-07-27 — Repository de leitura do Senior

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 2 — Integração cadastral
O que foi concluído: repository Python sem models para Empresa → Filial → Tipo → Colaborador → Detalhe; DTOs imutáveis; validação de parâmetros; timeout por chamada; falha segura; logs de duração e quantidade.
Decisões: manter SQL runtime centralizado em apps/integrations/senior; lista não projeta CPF; detalhe retorna somente CPF mascarado; limite padrão de colaboradores 20 e máximo global 100.
Riscos: contrato SQL runtime e documento homologado devem evoluir juntos; 49 colaboradores seguem sem descrição de centro de custo; concorrência ainda não foi medida.
Pendências: expor a cascata em endpoints autenticados; homologar LEFT JOIN do centro de custo; criar snapshot na abertura do processo.
Próximo passo: implementar endpoints autenticados da cascata com validação e respostas de indisponibilidade.
Comandos executados: pytest; ruff; mypy; Django shell com cascata real usando SGPD e cinco SELECTs limitados.
Arquivos alterados: .env.example, apps/integrations/senior, config/settings/base.py, config/logging.py, tests/test_senior_repository.py e documentação em docs/SGPD.
Testes: 21 testes passaram; cascata Oracle real retornou uma linha por etapa; consultas entre 4,82 ms e 58,01 ms; USU_DATALT convertido em datetime; CPF confirmado como mascarado; nenhum DDL ou DML executado.
```

### 2026-07-27 — Endpoints autenticados da cascata Senior

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 2 — Integração cadastral
O que foi concluído: quatro endpoints GET autenticados para empresa, filial, tipo e colaborador; paginação sem COUNT; payload explícito; tradução segura de erros 400, 502 e 503.
Decisões: exigir IsAuthenticated mesmo antes da definição dos papéis; usar employee_type como parâmetro estável; omitir CPF de toda listagem HTTP; não expor endpoint de detalhe nesta etapa.
Riscos: autorização granular por papel/empresa/filial ainda depende da definição funcional de papéis; a UI da cascata ainda não existe.
Pendências: definir papéis e escopos; implementar seleção HTMX; criar o caso de uso de abertura e snapshot.
Próximo passo: obter os grants DDL para aplicar a base de autenticação ou, em paralelo, iniciar a UI HTMX da seleção cadastral.
Comandos executados: uv sync; pytest; ruff; mypy; Django check; execução direta das quatro APIViews autenticadas contra o Oracle real.
Arquivos alterados: pyproject.toml, uv.lock, config/urls.py, apps/integrations/senior/api.py, apps/integrations/senior/urls.py, tests/test_senior_api.py e documentação em docs/SGPD.
Testes: 31 testes passaram; acesso anônimo bloqueado; quatro views reais responderam 200 com uma linha por etapa; consultas entre 0,70 ms e 39,46 ms; payload de colaborador sem campo CPF; nenhum DDL ou DML executado.
```

### 2026-07-27 — Grants mínimos para migrations no SGPD

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 1 — Fundação técnica / Oracle
O que foi concluído: conta SGPD e tablespace padrão inspecionados pela conexão administrativa PRD@PIMSCS; privilégio CREATE TABLE e quota de 500 MB em PIMS_DATA concedidos ao próprio SGPD.
Decisões: manter usuário único SGPD conforme ADR-022; usar quota finita; não conceder ADMIN OPTION, UNLIMITED TABLESPACE, privilégios ANY, CREATE USER ou grants adicionais no VETORH.
Riscos: o owner permanece no runtime conforme risco já aceito; 500 MB deverão ser monitorados conforme o schema crescer.
Pendências: aplicar migrations somente após nova confirmação/revisão do plano e validar os objetos criados.
Próximo passo: executar migrate no DEV e verificar plano, objetos, índices, constraints, quota consumida e rollback operacional.
Comandos executados: inspeções read-only em DBA_USERS, SESSION_PRIVS, DBA_SYS_PRIVS, DBA_TS_QUOTAS e capacidade do PIMS_DATA; GRANT CREATE TABLE TO SGPD; ALTER USER SGPD QUOTA 500M ON PIMS_DATA; confirmação pela conexão Django SGPD.
Arquivos alterados: README.md e documentação em docs/SGPD.
Testes: SGPD confirmou USER_SYS_PRIVS = CREATE TABLE e USER_TS_QUOTAS = PIMS_DATA/500 MB; grant sem ADMIN OPTION; nenhum usuário criado; nenhum objeto Senior alterado.
```

### 2026-07-27 — Usuários, papéis, escopos e vínculo administrativo AD

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 1 — Base técnica / Identidade e autorização
O que foi concluído: manutenção server-side de usuários; autenticação local; troca obrigatória de senha temporária; papéis e cinco permissões delegáveis; atribuições globais, por empresa e por filial; validade e revogação lógica; vínculo/desvínculo AD administrativo; auditoria append-only de contas; autorização dos endpoints Senior por escopo; migrations e catálogo inicial aplicados no Oracle; primeira conta humana criada pelo bootstrap auditado; interpretação de vínculo AD ausente corrigida para a semântica de strings vazias do Oracle.
Decisões: usar services transacionais, lock pessimista e versão otimista; manter Django Admin somente leitura; tratar vínculo AD como registro administrativo sem ativar LDAP; manter nove papéis iniciais; usar permissões diretas como globais e permissões de papéis como escopadas; não criar conta humana nem senha automaticamente.
Riscos: autenticação AD real continua sem atributo, endpoint, TLS, base de busca e contingência homologados; owner SGPD permanece no runtime; conexão administrativa PRD@PIMSCS foi usada exclusivamente mediante autorização explícita para o grant mínimo; rollback para zero é destrutivo e não deverá ser usado após existir auditoria.
Pendências: homologar integração LDAP/AD futura; concluir SMTP e demais itens da fundação. Dados sensíveis, retenção e política ampla de auditoria foram postergados em 2026-07-28.
Próximo passo: concluir a seleção HTMX da cascata cadastral já autorizada por escopo; depois iniciar a configuração funcional, conforme checkpoint.
Comandos executados: pytest; ruff check/format; mypy; Django check; makemigrations --check; sqlmigrate 0001–0005; migrate --plan; migrate; bootstrap_roles duas vezes; bootstrap_identity_admin interativo; consultas read-only a USER_TABLES, USER_CONSTRAINTS, USER_INDEXES, USER_TS_QUOTAS e contagens de domínio; GRANT CREATE SEQUENCE TO SGPD sem ADMIN OPTION pela conexão administrativa autorizada.
Arquivos alterados: apps/accounts, apps/integrations/senior/api.py, config, templates, tests, README.md e documentação em docs/SGPD.
Testes: 53 testes passaram, incluindo bootstrap administrativo único e auditado, rejeição de permissão homônima de outro app e regressão da semântica Oracle para vínculo AD vazio; lint, format, mypy, Django check, manifesto e diff sem erros; 23 migrations aplicadas e plano final vazio; 12 constraints habilitados e validados; 4 índices SGPD explícitos; nove papéis, cinco permissões e uma conta humana presentes; bootstrap de papéis idempotente; conta ativa com senha utilizável, papel ADMIN_IDENTIDADE global e eventos de criação e atribuição auditados; 2 MB de 500 MB consumidos antes do bootstrap; smoke DEV com login 200, redirect anônimo 302, referência anônima 403 e readiness 200; nenhum objeto VETORH alterado.
```

### 2026-07-27 — Seleção HTMX da cascata Senior

```text
Data: 2026-07-27
Responsável: Codex
Fase: Fase 2 — Integração cadastral
O que foi concluído: seleção server-side Empresa → Filial → Tipo de colaborador → Colaborador; busca por nome ou matrícula; navegação condicionada por permissão; fragmentos HTMX com limpeza dos níveis descendentes; tratamento seguro de 400, 403, 502 e 503; runtime HTMX 2.0.10 e licença servidos localmente.
Decisões: reutilizar o repository e a autorização já homologados; manter endpoints HTML separados dos endpoints JSON; limitar colaboradores a 20 por busca; não criar snapshot nem persistir referências nesta etapa; não usar CDN.
Riscos: atualização futura do HTMX exige revisão explícita de versão, licença, hash e regressão; indisponibilidade do Senior continua impedindo novas seleções; snapshot permanece pendente para o caso de uso de abertura.
Pendências: validar o snapshot na Fase 4 e concluir itens operacionais restantes da Fase 1.
Próximo passo: iniciar a Fase 3 pela modelagem pequena e revisável de setores e seus escopos, sem antecipar o workflow.
Comandos executados: pytest; ruff check/format; mypy; Django check; makemigrations --check; findstatic; collectstatic; smoke somente leitura da página e dos três fragmentos contra o Oracle DEV.
Arquivos alterados: apps/integrations/senior, apps/accounts/context_processors.py, config, templates, static/vendor/htmx, tests/test_senior_ui.py, README.md e documentação em docs/SGPD.
Testes: 62 testes passaram; nove cobrem a UI HTMX; lint, format, mypy, Django check e migrations sem divergências; HTMX local encontrado e coletado pelo WhiteNoise; smoke Oracle real retornou 200 na página e nos três fragmentos, com sete empresas na página e cinco colaboradores no probe final, sem CPF no HTML; nenhum DML ou DDL executado.
```

### 2026-07-28 — Homologação do centro de custo, concorrência e SMTP

```text
Data: 2026-07-28
Responsável: Codex
Fase: Fase 1 — Base técnica / Fase 2 — Integração cadastral
O que foi concluído: LEFT JOIN de R018CCU homologado por contagem global; benchmark read-only da consulta de colaboradores executado com 1, 5 e 10 conexões; conectividade SMTP Microsoft 365 testada.
Decisões: preservar colaboradores sem referência de centro de custo; postergar dados sensíveis, retenção e política ampla de auditoria; retirar do escopo documental as definições operacionais do storage de evidências solicitadas nesta revisão.
Riscos: SMTP AUTH foi recusado com 535 5.7.139; Send As não pôde ser exercitado. A medição de concorrência representa somente a carga controlada do DEV.
Pendências: corrigir a credencial ou política de SMTP AUTH e validar Send As; definir estratégia de homologação e monitoramento do contrato Senior.
Próximo passo: estabilizar e versionar o checkpoint atual antes de iniciar a configuração funcional.
Comandos executados: envio SMTP único pelo backend Django; scripts/oracle/run_senior_contract_validation.sh; uv run python scripts/oracle/benchmark_senior_concurrency.py.
Arquivos alterados: scripts/oracle/benchmark_senior_concurrency.py, scripts/oracle/validate_senior_reference_queries.sql e documentação em docs/SGPD.
Testes: SMTP alcançou o Microsoft 365 via TLS/STARTTLS, mas nenhuma mensagem foi enviada após recusa de autenticação; Oracle confirmou 1.891 elegíveis, 49 sem R018CCU, LEFT JOIN=1.891, INNER JOIN=1.842 e zero chaves R018CCU duplicadas; 80 consultas concorrentes concluídas sem erro ou timeout, com p95 máximo de 60,64 ms.
```

### 2026-07-28 — SMTP AUTH e Send As homologados

```text
Data: 2026-07-28
Responsável: Codex
Fase: Fase 1 — Base técnica
O que foi concluído: teste SMTP repetido após atualização das credenciais; Microsoft 365 aceitou uma mensagem de prova enviada ao próprio remetente configurado.
Decisões: considerar SMTP AUTH e Send As homologados no DEV.
Riscos: a entrega final na caixa postal ainda depende do processamento normal do Microsoft 365, mas o servidor aceitou o envio sem erro.
Pendências: nenhuma para a configuração SMTP atual.
Próximo passo: estabilizar e versionar o checkpoint atual antes de iniciar a configuração funcional.
Comandos executados: uv run manage.py shell --settings=config.settings.development com send_mail e fail_silently=False.
Arquivos alterados: README.md e documentação em docs/SGPD.
Testes: messages_sent=1, TLS habilitado, porta 587; nenhuma credencial foi exibida ou registrada.
```

### 2026-07-28 — Estabilização e versionamento do checkpoint técnico

```text
Data: 2026-07-28
Responsável: Codex
Fase: Fechamento das Fases 1 e 2
O que foi concluído: autorização administrativa reforçada no limite dos services; alteração e exclusão em lote da auditoria bloqueadas; desativação concorrente do último superusuário serializada; baseline das migrations de contas reconciliada com o Oracle DEV; código e testes versionados no commit local 4498ca8.
Decisões: manter dupla validação de autorização em views e services; preservar auditoria append-only também contra QuerySet.update e QuerySet.delete; bloquear os superusuários ativos em ordem determinística antes de desativação; considerar accounts.0001 a baseline final, pois nenhuma base conhecida recebeu sua forma preliminar e o primeiro migrate conhecido já criou SGPD_USER com ad_username anulável; migrations futuras serão somente incrementais.
Riscos: o uso do owner SGPD no runtime permanece aceito apenas no DEV; uma repetição do probe Oracle encontrou ORA-12560 após a confirmação bem-sucedida, mantendo o risco de indisponibilidade já registrado; a medição de concorrência do Senior representa somente a carga controlada do DEV.
Pendências: iniciar a Fase 3 pela modelagem pequena e revisável de setores e escopos; snapshot permanece para a abertura transacional da Fase 4; dados sensíveis, retenção e política ampla de auditoria permanecem postergados.
Próximo passo: iniciar a configuração funcional por setores, responsáveis e seus escopos, sem antecipar workflow ou snapshot.
Comandos executados: pytest; ruff check; ruff format --check; mypy; Django check; makemigrations --check --dry-run; showmigrations accounts; consulta read-only a USER_TABLES; migrate --plan tentado novamente; git diff --check; git add; git commit.
Arquivos alterados: apps/accounts, apps/integrations/senior, config, scripts/oracle, static/vendor/htmx, templates, tests, README.md e documentação em docs/SGPD.
Testes: 64 testes passaram; lint, format, mypy, Django check, migrations e diff sem divergências; accounts.0001–0005 confirmadas como aplicadas e catálogo confirmou SGPD_USER sem ACCOUNTS_USER; a repetição posterior do plano Oracle falhou antes de consultar o schema com ORA-12560, sem executar DDL ou DML.
```

### 2026-07-28 — Decisão da migração para SPA Angular

```text
Data: 2026-07-28
Responsável: Claude
Fase: Fase 2.5 — Migração da interface / Fase A
O que foi concluído: revisão completa da documentação e do código existentes; decisão explícita de substituir a interface Django Templates + HTMX + Alpine por SPA Angular; ADR-025, ADR-026, ADR-027 e ADR-028 registradas; ADR-002 marcada como substituída; plano de sete fases versionado em MIGRATION_FRONTEND_SPA.md; AGENTS.md, README.md, ARCHITECTURE.md, SECURITY.md, ENVIRONMENT.md, ROADMAP.md, RISK_REGISTER.md, INTEGRATION_SENIOR_ORACLE.md, PROMPT.md, CHECKPOINT.md e MANIFEST.json atualizados.
Decisões: adotar Angular 21 com PrimeNG 21 e preset Aura, espelhando a arquitetura do projeto corporativo de referência em /home/macari/dev/prdcana/frontend; autenticar por sessão Django com CSRF em origem única e não usar JWT, preservando a auditoria e a revogação de sessão já homologadas; servir a SPA pelo próprio Django com WhiteNoise, sem Nginx, mantendo a ADR-014; adotar mobile first como requisito, com uso exclusivo de min-width e proibição de max-width em código novo; substituir escopo total, contas e cascata Senior, preservando o Django Admin somente leitura; executar API primeiro e remoção por último, para que cada commit deixe o sistema utilizável.
Riscos: R38 a R43 registrados, com destaque para a ampliação da superfície de API sem autorização, a perda da imposição de troca de senha temporária ao substituir o redirecionamento e o risco de reintroduzir CSS desktop first ao portar SCSS da referência. R34, sobre a manutenção do runtime HTMX, foi encerrado porque o HTMX sai da stack.
Pendências: Fases B a G não iniciadas. A administração de contas continua sem API, o que a torna o item de maior esforço da migração. A interface server-side permanece em operação e não deve receber telas novas.
Próximo passo: executar a Fase B, criando o envelope de erro, a API de autenticação e contexto e a adaptação do middleware de senha temporária para respostas de API.
Comandos executados: inspeção da árvore e do histórico Git; leitura integral da documentação em docs/SGPD, AGENTS.md, README.md e PROMPT.md; leitura de apps/accounts, apps/integrations/senior, config e templates; inspeção do projeto de referência prdcana/frontend; verificação de Node, npm e Docker; validação SHA-256 do manifesto.
Arquivos alterados: AGENTS.md, PROMPT.md, README.md, docs/SGPD/MIGRATION_FRONTEND_SPA.md, docs/SGPD/DECISIONS.md, docs/SGPD/ARCHITECTURE.md, docs/SGPD/SECURITY.md, docs/SGPD/ENVIRONMENT.md, docs/SGPD/ROADMAP.md, docs/SGPD/RISK_REGISTER.md, docs/SGPD/INTEGRATION_SENIOR_ORACLE.md, docs/SGPD/CHECKPOINT.md e docs/SGPD/MANIFEST.json.
Testes: nenhum código foi alterado, portanto a suíte não foi reexecutada nesta fase; manifesto revalidado por SHA-256 com todos os arquivos íntegros; consistência cruzada da documentação verificada, sem referência remanescente a HTMX, Alpine, Tailwind ou daisyUI como stack vigente.
```

### 2026-07-28 — API de autenticação e contexto de autorização

```text
Data: 2026-07-28
Responsável: Claude
Fase: Fase 2.5 — Migração da interface / Fase B
O que foi concluído: envelope de erro único da API com handler do DRF; seis endpoints em /api/v1/auth/ para cookie CSRF, login, logout, usuário atual, contexto de autorização e troca da própria senha; limitação de tentativas de login; adaptação do PasswordChangeRequiredMiddleware para respostas de API; alinhamento dos endpoints cadastrais do Senior ao mesmo envelope; extração de active_assignments como definição única de atribuição válida.
Decisões: responder 401 quando não há sessão, em vez do 403 que o DRF produz por SessionAuthentication não publicar WWW-Authenticate, para que a SPA possa rotear ao login em vez de exibir erro; validar CSRF explicitamente no login, pois o DRF só o exige quando já existe sessão e o POST anônimo ficaria exposto a login CSRF; migrar os endpoints do Senior de {detail} para {code, message, details}, evitando dois formatos de erro na mesma API; não distinguir usuário inexistente, senha incorreta e conta inativa, retornando invalid_credentials em todos os casos; bloquear sob /api/ tudo exceto csrf, me, logout e change-password enquanto houver senha temporária pendente; manter as views HTML e seus testes intactos, pois a remoção pertence à Fase G.
Riscos: R39 mitigado com teste dedicado, mas o conjunto de rotas liberadas durante a senha temporária precisa ser revisto sempre que a API crescer. A limitação de tentativas usa o cache local do processo, adequado ao DEV e insuficiente caso surjam múltiplos processos. R38 permanece aberto até a Fase C, que expõe a administração de contas.
Pendências: Fase C, com usuários, papéis, atribuições, vínculo AD, permissões e auditoria. As mensagens dos validadores de senha chegam como erro não vinculado a campo, e não em new_password, porque o service invoca validate_password diretamente; aceitável para o formulário, revisar se a UX exigir.
Próximo passo: executar a Fase C, expondo os services administrativos como endpoints com teste de permissão negada em cada um.
Comandos executados: uv run pytest; uv run ruff check --fix; uv run ruff format; uv run mypy apps config tests manage.py; uv run manage.py check; uv run manage.py makemigrations --check --dry-run; conferência das rotas registradas; smoke somente leitura contra o Oracle DEV com o ciclo csrf, me anônimo, me autenticado, contexto, empresas e erros 400 e 405.
Arquivos alterados: config/api.py, config/urls.py, config/settings/base.py, apps/accounts/api.py, apps/accounts/api_urls.py, apps/accounts/serializers.py, apps/accounts/authorization.py, apps/accounts/middleware.py, apps/integrations/senior/api.py, tests/test_auth_api.py, tests/test_senior_api.py, .env.example e documentação em docs/SGPD.
Testes: 85 testes passaram, sendo 21 novos da API de autenticação, cobrindo 401 anônimo, login auditado, credenciais inválidas auditadas, ausência de CSRF, conta inativa, throttling, campos obrigatórios, logout auditado com encerramento de sessão, troca de senha com preservação da sessão, senha atual incorreta, confirmação divergente, senha fraca sem alteração, bloqueio por senha temporária, contexto sem papéis, contexto com escopo de empresa, contexto de superusuário, desaparecimento de atribuição revogada e método não permitido; ruff, format, mypy estrito, Django check e migrations sem divergência; smoke Oracle DEV retornou 7 empresas e contexto com o papel real ADMIN_IDENTIDADE; nenhum DDL ou DML executado.
```

### 2026-07-28 — API de administração de contas

```text
Data: 2026-07-28
Responsável: Claude
Fase: Fase 2.5 — Migração da interface / Fase C
O que foi concluído: onze rotas em /api/v1/accounts/ cobrindo usuários, redefinição de senha, papéis, atribuição e revogação, vínculo e desvínculo AD, catálogo de permissões delegáveis e auditoria; serializers de entrada; payloads explícitos de saída; autorização declarada por endpoint e reavaliada a cada requisição; paginação por offset e limit sem COUNT; tradução de recurso inexistente em 404 no handler de erro.
Decisões: manter os endpoints como casca fina sobre os services existentes, sem duplicar regra de negócio; declarar a permissão exigida no atributo required_permission da view e verificá-la por uma permission class do DRF, mantendo a revalidação do service como limite real de segurança; repetir no serializer a validação cruzada de escopo do papel, para devolver erro por campo, sem remover a validação do service e da constraint SGPD_CK_ROLE_SCOPE; usar payloads explícitos em vez de ModelSerializer, garantindo que hash de senha e campos internos nunca sejam projetados; exigir confirmação de senha na criação e na redefinição, em paridade com os formulários server-side; converter ObjectDoesNotExist em 404 no handler, evitando que um .get() de service vire 500 na nova superfície; separar as rotas em api_accounts_urls.py para preservar os nomes auth-api já em uso.
Riscos: R38 mitigado, com teste de negação anônima e de negação por falta de permissão para os quinze pares de rota e método, além de teste de ausência de efeito colateral e de não escalonamento entre permissões. As views HTML permanecem ativas e continuam sendo caminho alternativo até a Fase G. A paginação sem COUNT não informa o total, o que a SPA precisará tratar na navegação.
Pendências: Fase D, com o scaffold Angular, o shell e a autenticação. As telas de contas dependem apenas desta API.
Próximo passo: executar a Fase D, criando frontend/ com Angular 21 e PrimeNG, os tokens do SGPD, o shell mobile first e a tela de login, e integrando o build ao Django.
Comandos executados: uv run pytest; uv run ruff check --fix; uv run ruff format; uv run mypy apps config tests manage.py; uv run manage.py check; uv run manage.py makemigrations --check --dry-run; smoke somente leitura contra o Oracle DEV nas cinco listagens, no 404 e no acesso anônimo.
Arquivos alterados: apps/accounts/api_accounts.py, apps/accounts/api_accounts_urls.py, apps/accounts/serializers.py, config/api.py, config/urls.py, tests/test_accounts_api.py e documentação em docs/SGPD.
Testes: 143 testes passaram, sendo 58 novos da administração de contas; trinta deles são casos de negação parametrizados por rota e método; os demais cobrem criação auditada sem projeção de senha, confirmação divergente, justificativa obrigatória, e-mail duplicado, busca, teto de página, detalhe com atribuições, 404, versão desatualizada, incremento de versão, proteção do último superusuário ativo, redefinição de senha, criação de papel, rejeição de permissão não delegável, catálogo de permissões, atribuição com escopo de empresa, três escopos inconsistentes, revogação com trilha, atribuição a usuário inativo, vínculo e desvínculo AD auditados, identificador AD duplicado, leitura filtrada da auditoria e auditoria somente leitura; ruff, format, mypy estrito, Django check e migrations sem divergência; smoke Oracle DEV retornou 9 papéis, 5 permissões delegáveis e 11 eventos de auditoria; nenhum DDL ou DML executado além dos casos de teste em SQLite.
```

### 2026-07-28 — Scaffold Angular, shell mobile first e autenticação

```text
Data: 2026-07-28
Responsável: Claude
Fase: Fase 2.5 — Migração da interface / Fase D
O que foi concluído: diretório frontend/ com Angular 21, PrimeNG 21 e preset Aura; sistema de tokens do SGPD e pontos de quebra centralizados; core/auth com serviço por signals, guarda, interceptador e inicializador de sessão; core/config com todas as rotas da API tipadas; core/layout com shell mobile first; core/theme com alternância clara e escura persistida; telas de login, troca da própria senha e painel; integração do build com o Django, servindo os assets pelo WhiteNoise na raiz e o index.html por view dedicada com cookie CSRF; catch-all com exclusão dos prefixos do backend; testes de frontend com Vitest.
Decisões: atualizar de Angular 21 e PrimeNG 21 para 22 por decisão explícita durante a execução; usar o suporte nativo de XSRF do HttpClient em vez de interceptador próprio, já que a origem é única e o cookie e o cabeçalho são os do Django; reduzir o interceptador ao que a sessão realmente exige, isto é, reagir a 401 e a password_change_required, sem refresh de token; resolver a senha temporária na própria guarda, que devolve UrlTree para a tela de troca conforme a URL de destino, evitando uma segunda guarda; servir o index.html por view Django e não pelo WhiteNoise, porque o storage com manifesto renomeia o arquivo e quebraria a rota raiz; usar WHITENOISE_ROOT para os assets, preservando a ADR-014; excluir api/, admin/, health/, static/, accounts/ e references/ do catch-all, para que rota inexistente de API devolva 404 em vez do HTML da SPA; reduzir os pesos de Kanit de seis para três, por peso de rede móvel.
Riscos: a atualização para a versão maior 22 do PrimeNG exigiu alterar templates, pois p-message deixou de aceitar a entrada text e a diretiva pButton deixou de aceitar label e icon; a nota de compatibilidade foi registrada na ADR-027. A conferência visual nos cinco pontos de quebra não foi executada por exigir navegador, e permanece como pendência declarada da fase. A limitação de tentativas de login continua usando o cache local do processo.
Pendências: conferência visual nos pontos de quebra; Fases E, F e G. As telas de contas e a cascata Senior dependem apenas de API já publicada.
Próximo passo: executar a Fase E, com as telas de usuários, papéis e auditoria, cada listagem em cartões no estado base e tabela a partir de md.
Comandos executados: npm install; npx ng build; npx ng test; uv run pytest; uv run ruff check --fix; uv run ruff format; uv run mypy apps config tests manage.py; smoke HTTP real com o servidor Django em 127.0.0.1:8123, cobrindo raiz, assets, rotas do cliente, prefixos de API, ciclo CSRF e login.
Arquivos alterados: frontend/ completo, apps/core/views.py, config/settings/base.py, config/urls.py, tests/test_spa.py e documentação em docs/SGPD.
Testes: 151 testes de backend passaram, sendo 8 novos do serviço da SPA, cobrindo shell na raiz com cookie CSRF, ausência de cache, três rotas do cliente, três rotas de API inexistentes devolvendo 404 em vez de HTML, health check não sombreado e ausência do bundle respondendo 503; 12 testes de frontend passaram em três arquivos, cobrindo estado anônimo inicial, persistência do usuário após login, ausência de qualquer dado de sessão no armazenamento local, limpeza no logout, exigência de troca de senha, derivação da visibilidade do menu, quatro casos da guarda e dois casos de filtragem do menu; bundle inicial de 504,89 kB brutos e 117,06 kB estimados de transferência, dentro do orçamento de 600 kB; build sem avisos; smoke HTTP confirmou index com app-root e csrftoken, assets e favicon servidos na raiz, /fe/* devolvendo o shell, /api/v1/auth/me/ anônimo em 401, rota de API inexistente em 404, login sem cabeçalho CSRF em 403 permission_denied e credencial inválida em 401 invalid_credentials.
```

### 2026-07-28 — Conferência visual e fixação do PrimeNG em MIT

```text
Data: 2026-07-28
Responsável: Claude
Fase: Fase 2.5 — Migração da interface / Fase D
O que foi concluído: conferência visual nos cinco pontos de quebra, executada em Chromium 150 com sessão autenticada real; correção de seis defeitos encontrados; retorno do par Angular e PrimeNG para a versão 21, última publicada sob MIT.
Decisões: fixar PrimeNG na 21 porque a 22 reclassificou o pacote como comercial e passou a exigir chave de licença mesmo no nível Community gratuito, injetando aviso permanente em todas as telas sem chave válida; fixar o Angular na 21 por consequência do peer dependency; conduzir a conferência contra SQLite efêmero, sem tocar o Oracle DEV; não tentar suprimir o aviso por CSS ou remoção de nó, por se tratar de controle de licença do fornecedor.
Riscos: R44 registrado, pois atualizar o PrimeNG passa a ser decisão de licenciamento e não apenas técnica. A conferência cobre os cinco pontos de quebra definidos e não substitui teste em aparelho físico.
Pendências: Fases E, F e G.
Próximo passo: executar a Fase E, com as telas de usuários, papéis e auditoria.
Comandos executados: npm install; npx ng build; npx ng test; uv run pytest; uv run ruff; uv run mypy; conferência em Chromium com puppeteer-core, cobrindo login, painel, gaveta, tema escuro, troca de senha e senha temporária.
Arquivos alterados: frontend/package.json, frontend/package-lock.json, frontend/src/styles.scss, frontend/src/app/app.config.ts, frontend/src/app/core/layout, frontend/src/app/features/login, frontend/src/app/features/senha e documentação em docs/SGPD.
Testes: 67 verificações automatizadas nos cinco pontos de quebra sem falha, cobrindo ausência de rolagem horizontal, alvos de toque de 44 px no estado base, campos com no mínimo 16 px no móvel, raiz de 16 px e 14 px conforme o ponto de quebra, menu filtrado pelo contexto do servidor, gaveta fora da tela por padrão e abrindo ao toque, barra lateral permanente a partir de 1024 px, alternância de tema e retenção do usuário com senha temporária na tela de troca; 151 testes de backend e 12 de frontend passaram; bundle inicial reduziu de 504,89 kB para 463,84 kB brutos.
Defeitos corrigidos: campo de usuário renderizava a 14 px no móvel, pois o seletor empatava em especificidade com o tema injetado em runtime e perdia por ordem, o que dispara zoom automático no iOS; grade do desktop com linha única deslocava a barra superior e empurrava a navegação para o rodapé; classes passadas por styleClass do PrimeNG não recebiam o atributo de encapsulamento, deixando o botão de menu visível no desktop e os botões de sessão sem largura total; gaveta iniciava sob a barra superior e ocultava o primeiro item do menu; botões de sessão em severidade secundária ficavam ilegíveis sobre o fundo escuro; campo de senha ficava mais estreito que os demais porque a classe não alcançava o host do componente.
```
