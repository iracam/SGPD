# Checkpoint do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Fase atual: Fases 1 e 2 estabilizadas; Fases 2.5 e 2.7 concluídas; Fase 3 ainda não iniciada
- Estado: SPA cobre autenticação, contas, configuração técnica LDAP e cascata Senior; interface server-side removida
- Banco: Oracle
- Backend: Django API-only, com Django Admin somente leitura preservado
- UI: SPA Angular 21 + PrimeNG 21, mobile first, decidida nas ADR-025 a ADR-028
- Integração principal: Senior HCM
- Autenticação: sessão Django com CSRF em origem única; local operacional;
  descoberta e login AD compartilham o transporte da ADR-032; LDAP simples
  funciona com warning e login AD permanece desligado até teste controlado

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
- [ ] Definir homologação operacional e monitoramento do contrato fora do
  probe controlado do DEV.
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
- [x] Implementar descoberta, importação explícita, vínculo verificado e
  backend AD, sem provisionamento implícito ou papéis derivados de grupos.
- [ ] Homologar URI, bind, cadeia TLS, bases e grupo/filtro no AD real com a
  Infraestrutura.
- [x] Definir origem dos usuários.
  - Todos os usuários, gestores, e-mails, papéis e escopos pertencem ao SGPD.
  - Uma conta pode ser cadastrada localmente ou criada explicitamente a partir
    de uma identidade AD; o login nunca provisiona conta.
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
- [x] Definir storage do DEV.
  - Filesystem local privado para evidências; storage corporativo de ambientes
    futuros exigirá nova decisão.
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
  - 25 migrations aplicadas; constraints SGPD habilitadas e validadas.
- [x] Cadastro e manutenção auditada de usuários.
- [x] Autenticação local e troca obrigatória de senha temporária.
- [x] Papéis, permissões e escopos.
- [x] Vínculo administrativo com o AD.
- [x] Descoberta, importação explícita e autenticação AD em estágios.
  - Django 5.2.16, DRF 3.17.1, `django-auth-ldap` 5.3.0 e
    `python-ldap` 3.4.7 bloqueados, sem regressão.
  - Ativação no diretório real permanece pendente de configuração homologada.
- [x] Auditoria de login, logout, falha e manutenção de contas.
- [x] Primeira conta humana de administração.
  - Criada pelo bootstrap interativo, com papel global
    `ADMIN_IDENTIDADE` e dois eventos de auditoria.
- [x] SMTP AUTH e `Send As`.
  - O Microsoft 365 aceitou uma mensagem de prova enviada ao próprio remetente
    configurado em 2026-07-28.
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
- [x] Cascata funcionando no repository, endpoints autenticados e SPA Angular.
- [x] Autorização da cascata por permissão, empresa e filial.
- [x] `LEFT JOIN` de centro de custo homologado.
  - Na validação mais recente de 2026-07-28, preservou 1.902 elegíveis;
    `INNER JOIN` excluiria os 49
    colaboradores sem referência em `R018CCU`; nenhuma chave de centro de
    custo duplicada foi encontrada.
- [x] Concorrência inicial medida no DEV.
  - 80 consultas de colaboradores com 1, 5 e 10 conexões, sem erros ou
    timeouts; p95 máximo de 60,64 ms.

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
  - Criação local sem justificativa digitada, com motivo operacional
    padronizado pelo servidor na auditoria.
  - Papel inicial e escopo podem ser designados no mesmo cadastro manual;
    conta, atribuição e auditoria são atômicas e exigem `manage_users` e
    `manage_roles`.
  - Criação, reativação e atualização de atribuições não exigem justificativa
    digitada; a auditoria usa motivo padronizado e a revogação preserva
    justificativa obrigatória.
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
  - 77 verificações automatizadas sem falha; sete defeitos corrigidos.
  - Inclui o recolhimento da barra lateral no desktop.
- [x] PrimeNG fixado na 21, última versão MIT.

### Fase E — Telas de contas

- [x] Usuários, com cartões no estado base e tabela a partir de `md`.
  - Listagem com busca, criação em diálogo e detalhe.
- [x] Detalhe do usuário: edição, redefinição de senha, atribuição e revogação
  de papéis, vínculo e desvínculo AD.
- [x] Papéis, com seleção das permissões delegáveis.
- [x] Auditoria, com filtro por tipo de evento e paginação sem total.
- [x] Troca da própria senha, entregue na Fase D.
- [x] Conferência visual nos cinco pontos de quebra.
  - 181 verificações sem falha; três defeitos corrigidos.

### Fase F — Cascata Senior

- [x] Seleção Empresa → Filial → Tipo → Colaborador na SPA.
  - Busca remota por nome ou matrícula com debounce de 400 ms, limite de 100
    caracteres e 20 resultados.
  - Consultas obsoletas canceladas e níveis descendentes limpos a cada troca.
- [x] Smoke somente leitura contra o Oracle DEV.
  - Quatro endpoints responderam `200` dentro de transação `READ ONLY`, sem CPF.
- [x] Conferência visual nos cinco pontos de quebra.
  - Executada em Chromium 150 contra SQLite efêmero e repository controlado.
  - Cinco breakpoints sem rolagem horizontal; tema escuro e resumo validados.

### Fase G — Remoção e limpeza

- [x] Templates, views HTML, forms e context processors removidos.
- [x] `ui_urls` e runtime HTMX removidos.
- [x] `staticfiles/` regenerado.
- [x] Testes acoplados à UI antiga removidos.
- [x] Suíte completa, lint, format, mypy e migrations sem divergência.
- [x] Checkpoint atualizado.

## Checkpoint 2.6 — Integração Active Directory

- [x] Separar descoberta e autenticação em chaves de ativação independentes.
- [x] Implementar cliente LDAP somente leitura, TLS obrigatório para
  autenticação, timeouts, paginação, limites e RootDSE.
- [x] Usar `objectGUID` como identificador estável e excluir contas
  desabilitadas.
- [x] Permitir filtro por OU, grupo direto/aninhado e filtro administrativo
  fixo.
- [x] Implementar pesquisa de grupos e usuários na API e na SPA.
- [x] Implementar criação explícita de usuário local já vinculado, sem papel
  automático e com senha inutilizável.
- [x] Revalidar no AD o vínculo posterior de conta local.
- [x] Implementar autenticação somente para conta previamente vinculada, sem
  provisionamento no login.
- [x] Bloquear fallback local para conta comum vinculada e preservar
  contingência configurável de superusuário.
- [x] Implementar system check, probe operacional, auditoria e testes.
- [x] Documentar `.env`, dependências nativas, filtros e comandos
  `ldapsearch` em `INTEGRATION_ACTIVE_DIRECTORY.md`.
- [x] Confirmar domínio, FQDN, portas, certificado e RootDSE.
  - `ad.bsa.local` resolve para `192.168.1.20`; LDAP 389 e LDAPS 636 acessíveis.
  - RootDSE confirmou `DC=bsa,DC=local`; certificado identifica
    `ad.bsa.local` e foi emitido por `BSA-AD-CA`.
- [x] Validar bind técnico, bases e DN exato do grupo `BSA_SGPD`.
  - A primeira validação usou a exceção histórica da ADR-030, substituída pela
    escolha única de transporte da ADR-032.
  - Filtro encontrou quatro usuários ativos elegíveis, sem exibir identidades.
- [x] Executar probe e filtro contra o AD corporativo.
- [ ] Se TLS for escolhido, instalar a CA `BSA-AD-CA` e repetir o probe.
- [ ] Executar importação/vínculo e login AD controlados com o transporte
  escolhido pelo SuperAdmin.

## Checkpoint 2.7 — Configuração técnica LDAP/Autenticação

- [x] Criar seção de menu e central de Configurações somente para SuperAdmin.
- [x] Criar cards para LDAP e módulos futuros.
- [x] Implementar guarda de rota e API com autoridade direta por
  `is_superuser`, sem permissão delegável.
- [x] Persistir singleton LDAP versionado no schema SGPD com baseline do
  `.env`.
- [x] Cifrar senha de bind e nunca projetá-la ou auditá-la.
- [x] Implementar upload privado de CA, limite, normalização PEM, hash e
  validação X.509.
- [x] Implementar validação não persistente do contrato.
- [x] Implementar teste de bind e RootDSE sem listar dados pessoais.
- [x] Aplicar uma escolha única de transporte a descoberta e login: LDAPS e CA
  quando TLS estiver marcado; LDAP simples com warning quando desmarcado.
- [x] Exigir probe correspondente e contingência local antes de ativar login
  AD.
- [x] Remover o campo de exceção DEV e a seleção de grupo adicional na
  importação.
- [x] Permitir buscar o grupo obrigatório em modal na central de Configurações,
  aberto pelo botão ao lado do campo de DN e com mínimo de dois caracteres.
- [x] Manter campos e botões com alvo de 44 px no móvel e a mesma densidade
  compacta no desktop, pelo token global `--control-height`.
  - Servidor LDAP, conta técnica e senha dividem a mesma linha a partir de
    `lg`, permanecendo empilhados no móvel.
- [x] Auditar atualização, upload e teste com correlation ID.
- [x] Cobrir autorização, versão concorrente, segredo, certificado, probe,
  API, guarda, menu e tela com testes automatizados.
- [ ] Aplicar no Oracle DEV a migration revisada que remove a coluna legada
  `ALLOW_INSECURE_DISCOVERY`.

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
- [ ] Snapshot histórico.
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

## Registro histórico de execuções

Os registros abaixo preservam o contexto conhecido em cada execução e não são
normativos. Pendências e próximos passos antigos podem ter sido resolvidos
depois; o estado vigente é definido pelo status geral e pelos checklists acima.

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

### 2026-07-28 — Correção do recolhimento da barra lateral

```text
Data: 2026-07-28
Responsável: Claude
Fase: Fase 2.5 — Migração da interface / Fase D
O que foi concluído: correção do recolhimento da barra lateral no desktop, que ocultava os rótulos mas mantinha a coluna na largura expandida; nomes acessíveis nos botões de sessão; extensão da conferência visual para exercitar o recolhimento.
Decisões: declarar a largura recolhida como variante da grade, e não apenas ocultar rótulos; empilhar marca e botão na topbar quando recolhida, para caberem em 4,5 rem; reduzir os botões de sessão a ícone quando recolhidos e suprir o nome acessível por ariaLabel, já que o rótulo em display none sai da árvore de acessibilidade.
Riscos: nenhum novo. O defeito passou pela conferência anterior porque o script não exercitava o botão de recolher; a lacuna foi fechada com cinco verificações novas por ponto de quebra de desktop.
Pendências: Fases E, F e G.
Próximo passo: executar a Fase E.
Comandos executados: npx ng build; conferência em Chromium; uv run pytest; uv run ruff; uv run mypy; npx ng test.
Arquivos alterados: frontend/src/app/core/layout/authenticated-layout.scss, frontend/src/app/core/layout/authenticated-layout.html e docs/SGPD/CHECKPOINT.md.
Testes: 77 verificações nos cinco pontos de quebra sem falha, incluindo estreitamento efetivo da coluna de 17 rem para 4,5 rem, deslocamento do conteúdo, ocultação dos rótulos, preservação do nome acessível e ausência de rolagem horizontal ao recolher; 151 testes de backend e 12 de frontend passaram.
```

### 2026-07-28 — Telas de contas na SPA

```text
Data: 2026-07-28
Responsável: Claude
Fase: Fase 2.5 — Migração da interface / Fase E
O que foi concluído: telas de usuários, detalhe do usuário, papéis e auditoria; utilitário compartilhado de tradução do envelope de erro em erros por campo; padrão único de listagem responsiva; testes de frontend das novas telas; conferência visual estendida às telas administrativas.
Decisões: substituir o componente de tabela do PrimeNG por tabela semântica, porque a listagem não usa ordenação, filtro nem paginação do componente e ele custava 487 kB por tela, dos quais nada aparece no móvel; concentrar as ações auditadas do usuário em diálogos sobre a tela de detalhe, mantendo uma única rota por entidade; declarar o padrão de listagem em um parcial SCSS compartilhado, para que cartões no estado base e tabela a partir de md sejam a regra e não a exceção; usar controle de formulário com lista de identificadores para as permissões do papel, em vez de estado paralelo; assumir na auditoria que há próxima página quando a atual vem cheia, já que a API não faz COUNT por decisão de desempenho.
Riscos: nenhum novo. A paginação sem total continua sendo aproximação, registrada desde a Fase C. As telas dependem apenas de API já coberta por teste de permissão negada.
Pendências: Fase F, com a cascata cadastral do Senior, e Fase G, com a remoção da interface server-side.
Próximo passo: executar a Fase F.
Comandos executados: npx ng build; npx ng test; uv run pytest; uv run ruff; uv run mypy; conferência em Chromium com dois atores, um com escopo parcial e outro com todas as permissões.
Arquivos alterados: frontend/src/app/core/api, frontend/src/app/features/usuarios, frontend/src/app/features/papeis, frontend/src/app/features/auditoria, frontend/src/app/fe.routes.ts, frontend/src/styles.scss, frontend/src/styles/_listagem.scss e documentação em docs/SGPD.
Testes: 181 verificações visuais nos cinco pontos de quebra sem falha, incluindo cartões no estado base e tabela a partir de md em cada listagem, presença de dados, diálogo cabendo no viewport e ausência de rolagem horizontal; 23 testes de frontend em cinco arquivos, cobrindo o utilitário de erro, a dupla representação da listagem, o estado vazio, os selos de senha temporária e conta inativa e a exibição da mensagem do envelope em falha de permissão; 151 testes de backend inalterados.
Defeitos corrigidos: a entrada label do componente de checkbox não renderiza texto nesta versão, deixando três campos sem rótulo visível; o alvo clicável do checkbox media 20 px, abaixo do mínimo de toque; o diálogo de formulário longo estourava a altura da tela e deixava as ações fora de alcance, agora com rolagem interna; o host do campo de senha não ocupava a largura, correção promovida ao escopo global; a margem padrão do elemento de lista de definição afastava os campos do cartão.
```

### 2026-07-28 — Cascata Senior na SPA

```text
Data: 2026-07-28
Responsável: Codex
Fase: Fase 2.5 — Migração da interface / Fase F
O que foi concluído: feature Colaboradores na rota /fe/colaboradores, com seleção Empresa → Filial → Tipo → Colaborador sobre os quatro endpoints existentes; busca remota pelo filtro do p-select; resumo somente leitura; estados de carregamento, vazio, erro e nova tentativa; testes de frontend; smoke Oracle e conferência visual responsiva.
Decisões: manter backend, repository, SQL, grants e migrations inalterados; usar limites 100/100/100/20 já homologados; cancelar requisições obsoletas com switchMap; limpar seleções descendentes imediatamente; aplicar debounce de 400 ms e máximo de 100 caracteres; preservar a interface server-side até a Fase G; não projetar CPF, persistir referência ou criar snapshot.
Riscos: respostas fora de ordem foram mitigadas por cancelamento testado; indisponibilidade do Senior permanece explícita e recuperável; a conferência em Chromium não substitui teste futuro em aparelho físico.
Pendências: Fase G, com remoção dos templates, views HTML, forms, context processors, ui_urls, HTMX, staticfiles e testes antigos.
Próximo passo: executar a Fase G em alteração separada, preservando Django Admin e toda a API.
Comandos executados: npm test -- --watch=false; npm run build; uv run pytest; uv run ruff check .; uv run ruff format --check .; uv run mypy apps config tests manage.py; uv run manage.py check; uv run manage.py makemigrations --check --dry-run --settings=config.settings.test; smoke dos quatro endpoints em transação Oracle READ ONLY; conferência em Chromium 150 nos breakpoints 360, 390, 768, 1024 e 1440 px; busca por max-width e CPF.
Arquivos alterados: frontend/src/app/features/colaboradores, frontend/src/app/fe.routes.ts, README.md e documentação em docs/SGPD.
Testes: 32 testes frontend passaram, nove novos da cascata; 151 testes backend passaram; build inicial de 495,26 kB dentro do orçamento; Ruff, format, mypy, Django check e migrations sem divergência; smoke Oracle retornou 200/200/200/200 com 7/1/1/5 resultados, transação READ ONLY e nenhum CPF; conferência visual passou nos cinco pontos de quebra, com uma coluna em 360/390, grade 2×2 em 768, quatro colunas em 1024/1440, filtro a 16 px e controles de 46 px no móvel, sem rolagem horizontal.
```

### 2026-07-28 — Remoção da interface server-side

```text
Data: 2026-07-28
Responsável: Codex
Fase: Fase 2.5 — Migração da interface / Fase G
O que foi concluído: remoção integral dos 14 templates de aplicação, views HTML e URLconfs de contas e da cascata Senior, forms, context processor, decorador de autorização exclusivo da UI, runtime e licença HTMX e testes acoplados à interface antiga; configuração de templates limitada ao Django Admin; staticfiles regenerado sem HTMX; documentação e manifesto atualizados.
Decisões: preservar Django Admin somente leitura, toda a API, services, autorização, auditoria, repository e SQL Senior; fazer /accounts/* e /references/* caírem no shell da SPA em vez de manter superfícies funcionais paralelas; redirecionar navegação com senha temporária para /fe/senha e manter o 403 tipado sob /api/; não alterar dependências, migrations, schema, grants ou dados.
Riscos: R45 registrado. O npm reporta três vulnerabilidades moderadas apenas na cadeia de desenvolvimento do Angular CLI, originadas no servidor estático Hono e aplicáveis a path traversal no Windows; o runtime possui zero vulnerabilidades segundo npm audit --omit=dev, o DEV homologado usa Debian e a correção automática exigiria alteração incompatível do Angular CLI. A conferência visual da Fase F permanece válida porque nenhum código da SPA ou SCSS foi alterado.
Pendências: iniciar a Fase 3 pela configuração funcional; snapshot continua reservado ao caso de uso transacional da Fase 4; dados sensíveis, retenção, política ampla de auditoria e autenticação AD real permanecem conforme checkpoints anteriores.
Próximo passo: iniciar a Fase 3 por setores e seus escopos, em mudança pequena e revisável.
Comandos executados: uv run pytest; uv run ruff check .; uv run ruff format --check .; uv run mypy apps config tests manage.py; uv run manage.py check; uv run manage.py makemigrations --check --dry-run --settings=config.settings.test; npm ci; npm test -- --watch=false; npm run build; uv run manage.py collectstatic --clear --noinput; npm audit e npm audit --omit=dev; smoke HTTP real do shell, rotas antigas, API anônima, Admin, estático do Admin e ausência do HTMX; scripts/oracle/run_senior_contract_validation.sh em acesso somente leitura.
Arquivos alterados: config/urls.py, config/settings/base.py, apps/accounts/authorization.py, apps/accounts/middleware.py, tests/test_spa.py, README.md e documentação em docs/SGPD; removidos apps/accounts/views.py, forms.py, context_processors.py e urls.py, apps/integrations/senior/views.py e ui_urls.py, templates/, static/vendor/htmx/ e os dois testes server-side antigos.
Testes: 139 testes backend e 32 testes frontend passaram; Ruff, format e mypy sem erros; Django check sem alertas; migrations sem divergência; build inicial de 495,26 kB dentro do orçamento; collectstatic removeu o HTMX antigo e regenerou 154 arquivos, com 444 pós-processados; smoke HTTP respondeu 200 para raiz, fallbacks /accounts/login/ e /references/senior/, Django Admin e CSS do Admin, 401 JSON tipado para API anônima e 404 para o runtime HTMX removido; contrato Oracle somente leitura retornou 7/1/1/5/1 nos probes, 1.902 elegíveis, 49 sem centro de custo e zero chaves duplicadas, sem DML ou DDL.
```

### 2026-07-28 — Revisão integral e consolidação documental

```text
Data: 2026-07-28
Responsável: Codex
Fase: Preparação da Fase 3
O que foi concluído: leitura e revisão cruzada dos 17 documentos Markdown vigentes; alinhamento do prompt operacional, arquitetura, ambiente, integração, segurança, roadmap e checkpoint ao estado posterior à Fase G; distinção explícita entre visão/requisitos/modelo alvo, componentes implementados e registros históricos; correção de rotas, paginação, versões, storage, middleware de senha, observabilidade e contrato da SPA; riscos resolvidos retirados da matriz ativa; manifesto regenerado.
Decisões: manter ADRs substituídas apenas como índice curto de rastreabilidade, sem conteúdo normativo; considerar o status geral e os checklists do checkpoint como fonte do estado atual, deixando o registro cronológico como histórico não normativo; manter a Fase 3 como próximo incremento e o snapshot exclusivamente na Fase 4; não alterar código, dependências, migrations, schema, grants ou dados nesta revisão.
Riscos: a remoção integral do histórico apagaria a justificativa de decisões de segurança e Oracle; o risco foi evitado preservando identificadores de ADR e registros cronológicos, mas removendo deles qualquer efeito normativo. Nenhum novo risco técnico foi introduzido.
Pendências: iniciar a Fase 3 por setores e seus escopos; homologação operacional do contrato Senior fora do probe DEV, dados sensíveis, retenção, política ampla de auditoria e autenticação AD real continuam pendentes nos checkpoints próprios.
Próximo passo: modelar o menor incremento de setores da Fase 3, com autorização, auditoria, compatibilidade Oracle, API e SPA.
Comandos executados: inventário de Markdown versionado; leitura integral e buscas cruzadas com rg; inspeção das rotas Django e Angular, settings e lockfiles; validação de links locais com Node; jq empty; git diff --check; regeneração e validação SHA-256 do manifesto.
Arquivos alterados: AGENTS.md, PROMPT.md, README.md, docs/SGPD/ARCHITECTURE.md, CHECKPOINT.md, DATA_MODEL.md, DECISIONS.md, ENVIRONMENT.md, INTEGRATION_SENIOR_ORACLE.md, MIGRATION_FRONTEND_SPA.md, REQUIREMENTS.md, RISK_REGISTER.md, ROADMAP.md, SECURITY.md, VISION.md, WORKFLOWS.md e MANIFEST.json. GLOSSARY.md foi revisado e não exigiu alteração.
Testes: 17 documentos Markdown vigentes com links locais válidos; arquivos JSON validados; manifesto íntegro por tamanho e SHA-256; busca de referências operacionais obsoletas sem divergência fora das seções históricas identificadas; diff sem erros de whitespace. A suíte de aplicação não foi repetida porque esta revisão alterou somente documentação; a validação completa registrada na Fase G permanece aplicável ao mesmo código.
```

### 2026-07-28 — Integração Active Directory

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.6 — Integração Active Directory
O que foi concluído: dependências LDAP nas versões mais recentes compatíveis sem regressão de Django ou DRF; configuração tipada e validada; cliente python-ldap somente leitura com TLS, RootDSE, paginação e filtros seguros; backend django-auth-ldap sem provisionamento implícito; criação local explícita já vinculada e vínculo posterior revalidado por objectGUID; bloqueio de fallback local para conta comum vinculada; APIs e interface Angular para status, grupos, usuários e importação; system check, probe operacional, testes e runbook.
Decisões: AD autentica e filtra elegibilidade, mas o SGPD continua proprietário de cadastro funcional, situação, papéis, permissões e escopos; objectGUID é a chave estável; descoberta e autenticação possuem chaves independentes; conta importada recebe senha inutilizável; somente superusuário local configurado pode servir de contingência; nenhum usuário ou papel é criado implicitamente pelo login ou por grupos.
Riscos: indisponibilidade/TLS do AD e base/filtro amplo registrados em R46 e R47; vínculo incorreto, fallback local e confusão entre capacidade implementada e homologação real mitigados em R21, R29 e R33.
Pendências: o .env real ainda precisa de URI com ldap:// ou ldaps://, bind inequívoco, CA e bases/grupo/filtro homologados; executar probe, buscas, importação e login no AD corporativo antes de habilitar autenticação.
Próximo passo: obter da Infraestrutura o domínio/base, DN ou UPN da conta técnica, cadeia de CA e grupo/OU elegível; habilitar primeiro somente LDAP_ENABLED e seguir o runbook.
Comandos executados: uv lock --upgrade-package django --upgrade-package djangorestframework --upgrade-package django-auth-ldap --upgrade-package python-ldap; uv sync --dev; suíte backend, Ruff, format, mypy, Django check, migrations check; suíte e build frontend; inspeção sanitizada do .env.
Arquivos alterados: pyproject.toml, uv.lock, .env.example, config/settings/base.py, apps/accounts, apps/integrations/active_directory, frontend/src/app/features/usuarios, README.md e documentação em docs/SGPD.
Testes: 165 testes backend e 33 testes frontend passaram; Ruff, format, mypy, Django check e migrations sem divergência; build inicial de 495,51 kB permaneceu abaixo do orçamento. O comando check_active_directory recusou corretamente a execução porque LDAP_ENABLED ainda está falso; o probe no AD real permanece pendente por configuração incompleta.
```

### 2026-07-28 — Descoberta do endpoint AD corporativo

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.6 — Homologação operacional do Active Directory
O que foi concluído: .env preparado, ainda desativado, com LDAPS ad.bsa.local:636, base ampla DC=bsa,DC=local e DNs candidatos para a OU Grupos e o grupo BSA_SGPD; DNS, portas, handshake TLS e RootDSE inspecionados sem usar credenciais.
Decisões: usar FQDN, e não IP, para preservar a validação do certificado; manter LDAP_ENABLED e LDAP_AUTHENTICATION_ENABLED falsos até instalar a CA e validar o bind; tratar os DNs derivados do caminho amigável como candidatos até confirmação autenticada.
Riscos: o certificado é emitido pela CA interna BSA-AD-CA, ainda ausente do trust store; habilitar agora falharia de forma segura. A existência da OU e do grupo não pôde ser confirmada anonimamente porque o AD exige bind.
Pendências: obter a CA BSA-AD-CA em PEM/CRT por canal confiável; preencher UPN/DN e senha da conta técnica; confirmar os DNs; executar check_active_directory, busca, importação e login controlado.
Próximo passo: instalar a CA e preencher o bind; habilitar somente LDAP_ENABLED para o primeiro probe.
Comandos executados: resolução DNS; teste TCP 636/389; openssl s_client com verificação e inspeção de metadados; ldapsearch anônimo do RootDSE; tentativa anônima controlada de validar os DNs, recusada pelo AD por exigir bind.
Arquivos alterados: .env local, docs/SGPD/INTEGRATION_ACTIVE_DIRECTORY.md, ENVIRONMENT.md, CHECKPOINT.md e MANIFEST.json.
Testes: ad.bsa.local resolveu para 192.168.1.20; portas 636 e 389 aceitaram conexão; certificado apresentou CN/SAN ad.bsa.local, emissor BSA-AD-CA e validade de 2026-02-09 a 2027-02-09; RootDSE confirmou defaultNamingContext DC=bsa,DC=local; nenhum segredo foi exibido ou transmitido.
```

### 2026-07-28 — Exceção temporária de descoberta LDAP sem TLS

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.6 — Homologação operacional do Active Directory
O que foi concluído: suporte explícito a LDAP simples somente para descoberta no DEV; LDAP_ALLOW_INSECURE_DISCOVERY protegido por DEBUG=true e incompatível com autenticação AD; warning no system check, API e SPA; settings de teste isolados do endpoint real; .env ativado em ldap://ad.bsa.local:389; bind, RootDSE, bases, DN exato do grupo e filtro de membros ativos validados.
Decisões: aceitar temporariamente o risco do bind técnico sem criptografia por instrução explícita; manter LDAP_AUTHENTICATION_ENABLED=false e bloquear login AD no backend até restaurar TLS; registrar a exceção na ADR-030 e o risco R48.
Riscos: usuário e senha da conta técnica trafegam sem criptografia na rede DEV. Nenhuma senha de usuário final foi transmitida; o modo é proibido em HML/PRD.
Pendências: obter e instalar BSA-AD-CA, retornar a LDAPS 636, remover LDAP_ALLOW_INSECURE_DISCOVERY e somente então homologar importação/vínculo e login.
Próximo passo: testar pesquisa administrativa e vínculo controlado na SPA; em paralelo, obter a CA para encerrar a exceção.
Comandos executados: manage.py check; check_active_directory; bind LDAP simples; busca exata do DN do grupo; filtro ativo e associação aninhada limitado a 50 resultados; suítes backend/frontend e validações estáticas.
Arquivos alterados: .env, .env.example, config/settings/base.py, config/settings/test.py, apps/integrations/active_directory, comando check_active_directory, frontend de usuários, testes e documentação em docs/SGPD.
Testes: probe confirmou bind e RootDSE; CN=BSA_SGPD,OU=Grupos,OU=BSAbioenergia,DC=bsa,DC=local retornou exatamente um grupo; filtro encontrou quatro usuários ativos elegíveis sem exibir identidades; warning sgpd.AD900 emitido; autenticação permaneceu desligada; 169 testes backend e 34 frontend passaram; Ruff, format, mypy, Django check de testes e migrations sem divergência; build inicial de 495,51 kB.
```

### 2026-07-28 — Compatibilidade Oracle no provisionamento pelo AD

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.6 — Homologação operacional do Active Directory
O que foi concluído: correção do erro 500 no POST /api/v1/accounts/directory/users/create/, causado pela combinação SELECT ... FOR UPDATE com FETCH FIRST gerada por first()/exists() e não suportada pelo backend Oracle; revisão de todos os bloqueios pessimistas do módulo de contas; correção preventiva do mesmo padrão na atribuição de papel.
Decisões: usar get() nas consultas bloqueadas cobertas por chaves únicas, pois o Django omite o limite quando o backend declara supports_select_for_update_with_limit=false; materializar sem slicing os pequenos conjuntos candidatos de conflito por login e e-mail; preservar transaction.atomic(), idempotência por objectGUID, constraints, tratamento de corrida por IntegrityError e auditoria existente.
Riscos: nenhum schema, dado, dependência, configuração LDAP ou regra de autorização foi alterado. A consulta bloqueada sem correspondência não bloqueia uma linha inexistente; a proteção final contra corrida continua nas constraints únicas do Oracle e na tradução de IntegrityError já existente.
Pendências: repetir pela SPA a criação da identidade que originou o erro para confirmar o ciclo HTTP completo no processo de desenvolvimento já recarregado.
Próximo passo: repetir a ação Criar usuário local na SPA; o endpoint responde HTTP 201 tanto na primeira execução quanto na repetição idempotente e devolve a conta vinculada.
Comandos executados: busca integral por select_for_update; testes direcionados; suíte backend completa; Ruff; format; mypy; inspeção de migrations e diff.
Arquivos alterados: apps/accounts/services.py, tests/test_active_directory.py, tests/test_accounts_services.py, docs/SGPD/CHECKPOINT.md e docs/SGPD/MANIFEST.json.
Testes: 171 testes backend passaram; dois testes novos simulam as capacidades relevantes do Oracle (FOR UPDATE disponível e FOR UPDATE com limite indisponível) e falhariam com o padrão anterior; mypy sem erros; Ruff e format sem divergência; nenhuma migration criada.
```

### 2026-07-28 — Reset operacional do schema SGPD DEV

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.6 — Homologação operacional do Active Directory
O que foi concluído: limpeza integral e explicitamente solicitada dos dados funcionais do schema Oracle SGPD para reiniciar os testes de criação e vínculo AD; usuários, superusuários, sessões, papéis, atribuições e auditoria foram zerados.
Decisões: executar django-admin flush, preservando estrutura, tabelas e histórico de migrations; revisar previamente o SQL gerado e confirmar CURRENT_SCHEMA=SGPD e as 14 tabelas-alvo; não executar rollback de migrations, DROP, DML no Senior ou alteração no owner VETORH.
Riscos: o flush usa TRUNCATE no Oracle e os dados removidos não são recuperáveis pela aplicação; eventual recuperação depende de backup externo. A operação foi autorizada explicitamente para o ambiente DEV. O warning AD900 permanece esperado enquanto a descoberta LDAP simples estiver ativa.
Pendências: recriar o catálogo de papéis e a primeira conta administrativa pelo bootstrap auditado; repetir a importação/vinculação controlada do AD.
Próximo passo: executar bootstrap_roles e, em seguida, bootstrap_identity_admin; autenticar na SPA e repetir o fluxo de criação local a partir da identidade AD.
Comandos executados: inspeção somente leitura de CURRENT_SCHEMA e USER_TABLES; sqlflush; flush --noinput; contagens pós-reset; verificação de constraints e migrate --check.
Arquivos alterados: somente dados no schema Oracle SGPD e documentação em docs/SGPD/CHECKPOINT.md e MANIFEST.json; nenhum código, migration, dependência ou configuração foi alterado.
Testes: users=0, superusers=0, roles=0, role_assignments=0, account_audit=0 e sessions=0; 23 migrations preservadas; 9 content types e 41 permissões padrão recriados pelo post_migrate; zero constraints desabilitadas; migrate --check sem pendências.
```

### 2026-07-28 — Importação AD sem justificativa e política única de senha local

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.6 — Homologação operacional do Active Directory
O que foi concluído: remoção da justificativa manual na criação de conta a partir do AD; auditoria preservada com motivo operacional padronizado; botão Criar vinculada habilitado somente quando a identidade possui sAMAccountName, givenName, sn e mail e não possui vínculo ou conflito local; mensagem em português para cada atributo ausente; política única de senha local aplicada pelo backend de autenticação, services, API e SPA.
Decisões: o POST de importação recebe somente objectGUID e o servidor reconsulta a identidade; importação é uma operação determinística cuja origem, ator e motivo não dependem de texto livre; vínculo e desvínculo posteriores continuam exigindo justificativa; local_password_allowed é calculado no servidor e projetado no usuário; conta comum vinculada pode receber e usar senha local enquanto LDAP_AUTHENTICATION_ENABLED=false, mas definição, redefinição, troca e fallback são bloqueados quando o login AD está ativo; superusuário só conserva senha local quando LDAP_LOCAL_SUPERUSER_FALLBACK=true.
Riscos: mitigado R29 também na manutenção de senha, eliminando a possibilidade de gravar uma credencial que a política de login recusaria. A autenticação local temporária de conta vinculada continua possível no DEV enquanto o login AD estiver desligado e deve ser removida operacionalmente ao ativá-lo.
Pendências: recriar catálogo e superusuário após o reset já executado; repetir na SPA importação sem justificativa, redefinição e login local com autenticação AD desligada; após restaurar TLS, homologar visualmente o bloqueio com autenticação AD ativa.
Próximo passo: executar bootstrap_roles e bootstrap_identity_admin, importar uma identidade elegível, definir senha local e confirmar login enquanto LDAP_AUTHENTICATION_ENABLED=false.
Comandos executados: testes direcionados de accounts e Active Directory; suíte backend completa; Ruff; format; mypy; Django check; migrations check; suíte Vitest e build Angular.
Arquivos alterados: apps/accounts/api_accounts.py, api_directory.py, serializers.py e services.py; apps/integrations/active_directory/backends.py e config.py; frontend de usuários; testes backend/frontend; documentação e MANIFEST.json.
Testes: 176 testes backend e 38 testes frontend passaram; regressões cobrem importação sem reason, auditoria padronizada, requisitos ausentes, senha local funcional com AD desligado, bloqueio sem alteração/auditoria com AD ativo e contingência de superusuário ligada/desligada; Ruff, format e mypy sem erros; Django check e migrations sem divergência; build inicial de 495,51 kB dentro do orçamento.
```

### 2026-07-28 — Central de Configurações e administração LDAP

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.7 — Configuração técnica de autenticação
O que foi concluído: central de Configurações na SPA, com card ativo de LDAP/autenticação e reservas visuais para módulos futuros; seção de navegação e rotas restritas a SuperAdmin; singleton versionado SGPD_LDAP_CONFIG; senha de bind cifrada; upload privado de bundle CA PEM/DER; validação X.509, validade, BasicConstraints e hash SHA-256; validação não persistente dos parâmetros; teste salvo de bind e RootDSE; carregamento dinâmico pelo backend django-auth-ldap; proteção de ativação, rotação segura da CA e auditoria sem segredos.
Decisões: SuperAdmin técnico é exclusivamente User.is_superuser, atributo definido tanto pelo createsuperuser quanto pelo bootstrap_identity_admin, sem confusão com papel funcional; a API e cada service repetem essa autorização; o .env permanece como baseline até o primeiro salvamento; a configuração efetiva pode mudar sem reiniciar o processo; o certificado fica em storage privado e fora do WhiteNoise; o login AD só pode ser ativado com TLS, CA vigente, probe bem-sucedido da mesma versão/fingerprint e contingência local utilizável; atualização, upload e teste não dependem de justificativa digitada e recebem motivos operacionais padronizados no servidor; ADR-031 registrada.
Riscos: a primeira revisão do SQL revelou NVARCHAR2(2048), que o Oracle 19c recusou com ORA-00910; os campos DN/filtro foram limitados a 2000, o SQL foi novamente revisado e a migration aditiva aplicada. R49 registra exposição de segredo, CA inválida e ativação sem contingência. A exceção LDAP simples da ADR-030 e R48 continua ativa apenas para descoberta no DEV; o login AD permanece desligado.
Pendências: obter e enviar a BSA-AD-CA por canal confiável, retornar a LDAPS 636, executar o teste de conexão salvo e só então homologar a ativação do login AD; e-mail, arquivos/evidências e parâmetros do processo continuam apenas como cards de roadmap.
Próximo passo: instalar a BSA-AD-CA pela nova tela, retirar LDAP_ALLOW_INSECURE_DISCOVERY e homologar o login corporativo com conta controlada, preservando o SuperAdmin local.
Comandos executados: sqlmigrate e revisão de SQL Oracle; migrate e migrate --plan; inspeção somente leitura de tabela e constraints; uv lock --offline; pytest; Ruff; format; mypy; Django check; makemigrations --check; Vitest; build Angular; conferência em Chromium 150 nos breakpoints 360, 390, 768, 1024 e 1440 px.
Arquivos alterados: apps/system_settings; configuração e integração Active Directory; eventos de auditoria de accounts; frontend/src/app/features/configuracoes, guarda SuperAdmin, rotas e layout; pyproject.toml, uv.lock, .env.example; testes backend/frontend; README.md e documentação em docs/SGPD.
Testes: 199 testes backend e 44 testes frontend passaram; autorização negada testada para anônimo, usuário comum, staff e usuário com permissões funcionais; regressões cobrem cifra sem projeção, concorrência otimista, bloqueio de alteração/exclusão em lote, rollback de arquivo quando a auditoria falha, upload privado sem justificativa manual, PEM/DER, conteúdo inválido, certificado não CA ou expirado, rotação com desligamento do login, probe/fingerprint, corrida durante probe, bloqueios de ativação e auditoria. Ruff, format, mypy, Django check, migrations e build sem divergência; migration aplicada e plano final vazio. A conferência visual não encontrou overflow horizontal nos cinco pontos de quebra, manteve campos textuais a 16 px no móvel e confirmou os estados mobile e desktop.
```

### 2026-07-28 — Transporte LDAP único e formulários compactos

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.7 — Refinamento da configuração LDAP/Autenticação
O que foi concluído: campos de edição mantidos com alvo de toque de 44 px no móvel e reduzidos para 2,25 rem no desktop; configuração LDAP simplificada para uma única escolha “Negociar TLS”, próxima ao certificado da CA; endereço do servidor sem protocolo, com ldap:// ou ldaps:// e portas padrão montados automaticamente; remoção da exceção “Permitir LDAP simples somente no DEV”; descoberta, importação, vínculo e login usando o mesmo transporte; LDAP simples liberado por decisão explícita do SuperAdmin com aviso forte; importação sem grupo opcional e busca de grupos transferida para a central de Configurações, usando a configuração salva.
Decisões: TLS marcado significa LDAPS e exige CA válida; TLS desmarcado significa LDAP simples para todos os fluxos e não exige CA, mas mantém aviso de que a credencial técnica e a senha do usuário trafegam sem criptografia; ativação do login continua exigindo probe da mesma configuração e contingência local de SuperAdmin; base, grupo obrigatório e filtro adicional salvos são aplicados exatamente às buscas e ao login; esquemas informados manualmente são recusados pela API.
Riscos: LDAP simples mantém o risco muito alto R48 por decisão administrativa explícita; a conta técnica deve permanecer somente leitura e nenhuma credencial pode ser registrada. A migration 0002 remove definitivamente a coluna legada ALLOW_INSECURE_DISCOVERY; o SQL Oracle foi revisado, mas não aplicado ao DEV nesta execução.
Pendências: aplicar a migration system_settings 0002 no Oracle DEV em janela controlada; executar probe, descoberta e login controlado no AD real com o transporte escolhido; se TLS for escolhido, instalar antes a BSA-AD-CA.
Próximo passo: aplicar a migration revisada e homologar o fluxo completo no AD corporativo com uma conta controlada, preservando o SuperAdmin local.
Comandos executados: pytest; Ruff check e format; Mypy; Django check; makemigrations --check; sqlmigrate somente leitura contra Oracle; Vitest; build Angular; busca por media query max-width; diff check; conferência em Chromium 150 com SQLite efêmero; regeneração e validação do manifesto e dos links locais.
Arquivos alterados: configuração, cliente, backend e checks do Active Directory; central system_settings e migration 0002; APIs de diretório; configuração e telas Angular de LDAP e usuários; tokens globais de formulário; .env.example; testes; README.md e documentação em docs/SGPD.
Testes: 204 testes backend e 46 testes frontend passaram; Ruff, format e Mypy sem erros; Django check sem alertas; models e migrations sem divergência; build de produção concluído com bundle inicial de 496,08 kB; nenhuma media query max-width foi introduzida; diff sem erros de whitespace; manifesto de 19 arquivos e links locais de 16 documentos íntegros. O sqlmigrate confirmou somente ALTER TABLE SGPD_LDAP_CONFIG DROP COLUMN ALLOW_INSECURE_DISCOVERY, sem executar DDL. No Chromium, o campo de servidor mediu 31,5 px em 1440 px e 44 px em 390 px, sem overflow horizontal; o aviso forte apareceu somente com TLS desmarcado e os rótulos legados permaneceram ausentes.
```

### 2026-07-28 — Busca de grupo LDAP em modal

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.7 — Refinamento da configuração LDAP/Autenticação
O que foi concluído: botão Buscar grupo posicionado imediatamente ao lado do DN obrigatório; campo de pesquisa e resultados movidos para modal; pesquisa bloqueada até dois caracteres; seleção preenche o DN, marca o formulário como alterado e fecha o modal; servidor LDAP, conta técnica e senha alinhados na mesma linha no desktop.
Decisões: a busca continua usando exclusivamente a configuração LDAP já salva; o modal informa essa origem e mantém erros e estado vazio locais; a grade dos três campos passa a ter três colunas somente a partir de lg e permanece empilhada no móvel.
Riscos: nenhuma regra de autenticação, filtro, autorização, API, schema Oracle ou integração Senior foi alterada. A pesquisa real continua dependente de descoberta LDAP salva e operacional.
Pendências: permanecem a aplicação da migration system_settings 0002 no Oracle DEV e a homologação controlada do fluxo no AD real.
Próximo passo: aplicar a migration revisada e homologar busca, descoberta e login com o transporte escolhido.
Comandos executados: npm test -- --watch=false; npm run build; git diff --check; busca por media query max-width; conferência em Chromium 150 a 390 e 1440 px com SQLite efêmero.
Arquivos alterados: componente, template, SCSS e teste da configuração LDAP; docs/SGPD/CHECKPOINT.md; docs/SGPD/MANIFEST.json.
Testes: 46 testes frontend passaram; build de produção concluído com bundle inicial de 496,08 kB; modal abriu com busca desabilitada antes de dois caracteres e habilitada a partir de dois; em 1440 px os três campos mediram 347,41 px e tiveram o mesmo alinhamento vertical; em 390 px permaneceram empilhados; não houve overflow horizontal nem media query max-width.
```

### 2026-07-28 — Altura global de campos e botões

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.7 — Refinamento visual global
O que foi concluído: botões PrimeNG alinhados à altura já adotada pelos campos de edição; padrão centralizado no token global --control-height para ser herdado por todo o frontend.
Decisões: preservar 44 px para campos e botões no estado base móvel; aplicar a mesma altura compacta de 2,25 rem a ambos a partir de lg; manter o ajuste no stylesheet global, sem sobrescritas por feature.
Riscos: o padrão pressupõe botões de uma linha; novos rótulos extensos devem manter largura responsiva suficiente para não exigir quebra. Nenhum backend, regra de autorização, API, dependência, migration, schema Oracle ou integração Senior foi alterado.
Pendências: nenhuma no escopo deste refinamento; permanecem as pendências funcionais e operacionais dos checkpoints vigentes.
Próximo passo: seguir o checkpoint vigente, sem ajustes locais de altura em novas features.
Comandos executados: suíte Vitest; build Angular de produção; medição em Chromium nos viewports 390 e 1440 px; busca por media query max-width; revisão do diff e validação do manifesto.
Arquivos alterados: frontend/src/styles.scss; docs/SGPD/MIGRATION_FRONTEND_SPA.md; docs/SGPD/CHECKPOINT.md; docs/SGPD/MANIFEST.json.
Testes: 46 testes frontend passaram; build de produção concluído com bundle inicial de 496,12 kB; em 390 px, campo e botão mediram 44 px; em 1440 px, ambos mediram 31,5 px (2,25 rem); não houve overflow horizontal.
```

### 2026-07-28 — Criação local de usuário sem justificativa

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.7 — Refinamento da administração de contas
O que foi concluído: remoção da justificativa digitada no cadastro de usuário local; campo retirado da SPA e do contrato de entrada da API; CreateUserCommand simplificado; auditoria preservada com motivo operacional padronizado pelo backend.
Decisões: registrar “Criação explícita de conta local no SGPD.” em todo evento USER_CREATED originado pelo cadastro manual; manter ator, usuário-alvo, alterações permitidas e correlation ID; preservar justificativa obrigatória nas operações de edição, redefinição de senha, papéis, vínculo e desvínculo AD.
Riscos: a criação local deixa de receber contexto livre do operador por decisão explícita, mas continua integralmente atribuída ao ator autenticado e auditada. Nenhuma autorização, transação, senha, dependência, migration, schema Oracle ou integração Senior foi alterada.
Pendências: nenhuma no escopo deste refinamento; permanecem as pendências funcionais e operacionais dos checkpoints vigentes.
Próximo passo: seguir o checkpoint vigente e manter o motivo padronizado no servidor em novas superfícies de criação local.
Comandos executados: testes direcionados de services, API e tela de usuários; suíte backend completa; Ruff; format; Mypy; Django check; migrations check; suíte Vitest; build Angular; revisão do diff e validação do manifesto.
Arquivos alterados: services, serializer e API de accounts; formulário, models e testes da tela de usuários; testes backend; REQUIREMENTS.md; SECURITY.md; CHECKPOINT.md; MANIFEST.json.
Testes: 203 testes backend e 47 testes frontend passaram; Ruff, format e Mypy sem erros; Django check sem alertas; models e migrations sem divergência; build de produção concluído com bundle inicial de 496,12 kB.
```

### 2026-07-28 — Designação inicial de papel no cadastro de usuário

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.7 — Correção da administração de contas
O que foi concluído: diagnóstico do cadastro no frontend, API, services e Oracle DEV; papel e escopo iniciais adicionados como opção do cadastro manual; criação da conta e atribuição compostas na mesma transação; navegação ao detalhe após sucesso; erros aninhados do contrato projetados junto ao campo correto.
Decisões: preservar a criação sem papel para atores com apenas manage_users; exibir a designação inicial somente a quem possui manage_roles; ao selecionar papel, revalidar manage_users e manage_roles no backend; exigir justificativa específica da designação; registrar USER_CREATED e ROLE_ASSIGNED separadamente e desfazer ambos em qualquer falha; manter a importação AD sem papel automático.
Riscos: a operação composta poderia deixar uma conta órfã se não fosse atômica ou permitir escalonamento por um gestor apenas de usuários; ambos foram cobertos por rollback e autorização no service. Nenhuma migration, schema, dado, dependência ou integração Senior foi alterada.
Pendências: nenhuma no escopo da correção; atribuições adicionais e revogações continuam na tela de detalhe.
Próximo passo: usar o cadastro manual com um papel inicial e confirmar no detalhe; seguir depois o checkpoint vigente da Fase 3.
Comandos executados: leitura integral da documentação obrigatória; inspeção do diff local; testes direcionados e completos; consultas Oracle somente leitura por contagem; Ruff; format; Mypy; Django check; makemigrations check; Vitest; build Angular; busca por media query max-width; diff check.
Arquivos alterados: API, serializers, services e testes de accounts; contrato, formulário, estilos, serviço de erros e testes Angular de usuários; ARCHITECTURE.md, REQUIREMENTS.md, SECURITY.md, MIGRATION_FRONTEND_SPA.md, CHECKPOINT.md e MANIFEST.json.
Testes: 208 testes backend e 49 testes frontend passaram; Ruff, format e Mypy sem erros; Django check sem alertas; models e migrations sem divergência; build inicial de 496,12 kB dentro do orçamento; nenhuma media query max-width introduzida; diff sem erros de whitespace. O Oracle DEV foi consultado somente por contagens e confirmou duas contas para uma única atribuição prévia, evidenciando a lacuna sem executar DML ou DDL.
```

### 2026-07-28 — Atribuição de papel sem justificativa digitada

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.7 — Refinamento da administração de contas
O que foi concluído: justificativa livre removida da designação inicial no cadastro e da atribuição/reativação na tela de detalhe; contrato da API e comandos de service simplificados; auditoria preservada com motivo operacional padronizado pelo servidor.
Decisões: criação, reativação e atualização de atribuições registram “Designação explícita de papel no SGPD.” sem receber texto livre do cliente; ator, usuário, papel, escopo e validade continuam no evento ROLE_ASSIGNED; revogação permanece separada e exige justificativa humana.
Riscos: remover o campo do cliente não pode reduzir a rastreabilidade; o evento padronizado e seus dados estruturados foram mantidos e testados. Nenhuma autorização, transação, migration, schema, dado, dependência, integração Senior ou regra de revogação foi alterada.
Pendências: nenhuma no escopo desta alteração.
Próximo passo: validar visualmente o cadastro e o detalhe sem o campo de justificativa e seguir o checkpoint vigente da Fase 3.
Comandos executados: inspeção do fluxo compartilhado; testes direcionados e completos; Ruff; format; Mypy; Django check; makemigrations check; Vitest; build Angular; busca por media query max-width; diff check; validação do manifesto.
Arquivos alterados: API, serializer, services e testes de accounts; models, formulários e testes Angular de usuários e detalhe; ARCHITECTURE.md, REQUIREMENTS.md, SECURITY.md, MIGRATION_FRONTEND_SPA.md, CHECKPOINT.md e MANIFEST.json.
Testes: 208 testes backend e 50 testes frontend passaram; criação, reativação, autorização, rollback, auditoria padronizada e revogação foram cobertos; Ruff, format e Mypy sem erros; Django check sem alertas; models e migrations sem divergência; build inicial de 496,12 kB dentro do orçamento; nenhuma media query max-width introduzida; diff sem erros de whitespace.
```

### 2026-07-28 — Correção do envio da designação e observabilidade

```text
Data: 2026-07-28
Responsável: Codex
Fase: Checkpoint 2.7 — Correção da administração de contas
O que foi concluído: estado de usuários, atribuições e auditoria conferido no Oracle DEV; endpoint real reproduzido no schema SGPD dentro de transação revertida; causa localizada no botão PrimeNG do diálogo, cujo clique não disparava o submit; confirmação ligada explicitamente aos métodos Angular no cadastro e no detalhe; bloqueios de validação e falha do catálogo deixaram de ser silenciosos; logs JSON adicionados no recebimento e na conclusão da criação/designação.
Decisões: manter ngSubmit para teclado e onClick explícito para o botão PrimeNG; não criar evento de auditoria para operação que não chegou ao backend; usar logs operacionais para distinguir ausência de POST de falha transacional; projetar somente IDs técnicos, escopo, resultado e correlation ID, sem payload nem dados pessoais.
Riscos: o usuário ID 25 permanece sem atribuição porque o papel pretendido não pode ser inferido com segurança; nenhuma correção de dado foi aplicada. As reproduções Oracle consumiram somente valores de sequence dentro das transações revertidas, sem linha ou evento persistido. Nenhum objeto do Senior foi consultado ou alterado.
Pendências: o operador deve repetir a designação desejada para o usuário existente após publicar/reiniciar o código atualizado; a atribuição então deverá aparecer no detalhe, na auditoria ROLE_ASSIGNED e nos logs correlacionados.
Próximo passo: publicar o bundle e reiniciar o processo Django, repetir a designação do usuário ID 25 e confirmar a linha em SGPD_ROLE_ASSIGN e o evento ROLE_ASSIGNED.
Comandos executados: consultas Oracle somente leitura; reprodução do endpoint com rollback obrigatório; testes direcionados backend/frontend; Ruff e TypeScript; suítes completas, Mypy, Django check, migrations check, build Angular, diff check e validação do manifesto.
Arquivos alterados: API de accounts; formatter de logs; diálogo e testes Angular de usuários; testes backend; ARCHITECTURE.md, REQUIREMENTS.md, SECURITY.md, MIGRATION_FRONTEND_SPA.md, CHECKPOINT.md e MANIFEST.json.
Testes: 209 testes backend e 52 testes frontend passaram; o teste de interação reproduziu a ausência de chamada no clique antes da correção e confirmou o envio depois dela; Ruff, format, Mypy, TypeScript, Django check e migrations sem erros; build inicial de 496,12 kB dentro do orçamento. No Oracle, o endpoint respondeu 201, a atribuição e ROLE_ASSIGNED existiram dentro da transação, os logs account_role_assignment_requested/completed foram emitidos e o rollback preservou os contadores em zero.
```
