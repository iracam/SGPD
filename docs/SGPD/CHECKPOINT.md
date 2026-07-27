# Checkpoint do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Fase atual: Fase 0 — Descoberta e fundação
- Estado: Em andamento
- Banco: Oracle
- Backend: Django
- UI: Django Templates + HTMX + Alpine
- Integração principal: Senior HCM
- Autenticação prevista: Active Directory/LDAP

## Checkpoint 0 — Descoberta

### Ambiente

- [x] Confirmar sistema operacional do DEV: Debian 13.6, kernel 6.12, x86_64.
- [x] Confirmar versão do Python no ambiente local: CPython 3.13.5.
  - Homologação da versão do projeto permanece pendente.
- [x] Confirmar versão do Oracle Database: Oracle 19c.
- [x] Confirmar driver Oracle disponível.
  - Oracle Instant Client 19.28 em `/opt/oracle/instantclient_19_28`.
  - MCP Oracle SQLcl disponível com conexão DEV salva para Senior/Vetorh.
  - Pacote Python `oracledb` será instalado na fundação.
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

- [ ] Confirmar versão.
- [ ] Confirmar owner.
- [ ] Confirmar views disponíveis.
- [ ] Mapear empresa.
- [ ] Mapear filial.
- [ ] Mapear tipo de colaborador.
- [ ] Mapear colaborador.
- [ ] Mapear cargo.
- [ ] Mapear local.
- [ ] Mapear centro de custo.
- [ ] Mapear gestor.
- [ ] Mapear e-mail.
- [ ] Confirmar data de atualização.
- [ ] Confirmar regras de colaborador ativo.
- [ ] Definir estratégia de homologação.

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

- [ ] Definir grupos AD.
- [ ] Definir papéis.
- [ ] Definir escopo por empresa/filial.
- [ ] Definir dados sensíveis.
- [ ] Definir retenção.
- [ ] Definir acesso a documentos médicos.
- [ ] Definir acesso a valores.
- [ ] Definir política de auditoria.

### Arquitetura

- [x] Criar ADRs iniciais.
- [ ] Validar módulos Django.
- [ ] Definir estrutura de settings.
- [ ] Definir filas.
- [ ] Definir storage.
- [ ] Definir logging.
- [ ] Definir health checks.
- [ ] Definir backups.
- [ ] Definir observabilidade.

## Checkpoint 1 — Fundação técnica

- [x] Repositório criado.
- [ ] `pyproject.toml` criado.
- [ ] Django iniciado.
- [ ] Settings do DEV.
- [x] `.env.example`.
- [ ] Oracle conectado.
- [ ] Redis conectado, quando requerido.
- [ ] Worker conectado, quando requerido.
- [ ] Health check.
- [ ] Logging estruturado.
- [ ] Testes executando.
- [ ] Lint e format.
- [x] CI/CD não aplicável ao escopo atual.

## Checkpoint 2 — Integração cadastral

- [ ] Models `REF_*`.
- [ ] Views Senior definidas.
- [ ] Carga inicial.
- [ ] Incremental.
- [ ] Reconciliação.
- [ ] Logs.
- [ ] Reprocessamento.
- [ ] Cascata funcionando.
- [ ] Snapshot validado.

## Checkpoint 3 — Configuração funcional

- [ ] Setores.
- [ ] Responsáveis.
- [ ] Grupos.
- [ ] Regras.
- [ ] Templates.
- [ ] Versionamento.
- [ ] Permissões.

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
Riscos: filesystem com 96% de uso; Python ainda não homologado; serviços e ambientes corporativos indefinidos; toolchain global divergente.
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
Riscos: SMTP AUTH e Send As ainda precisam ser testados; backup, retenção e antivírus das evidências ainda precisam ser definidos.
Pendências: nenhuma no inventário Ambiente; instalações e testes seguem para a fundação técnica.
Próximo passo: iniciar o levantamento do Senior HCM ou homologar a fundação Django.
Comandos executados: confirmação oficial dos parâmetros SMTP e revisão cruzada da documentação.
Arquivos alterados: .env.example, README.md e documentação em docs/SGPD.
Testes: variáveis sem segredos; consistência documental; manifesto e links validados.
```
