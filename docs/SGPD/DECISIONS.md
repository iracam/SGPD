# Decisões Arquiteturais Iniciais

## ADR-001 — Django como framework principal

### Decisão

Usar Django como backend e camada web principal.

### Motivos

- maturidade;
- ORM;
- autenticação;
- admin;
- segurança;
- velocidade de entrega;
- experiência existente da equipe;
- integração adequada com Oracle;
- boa aderência a sistemas corporativos.

## ADR-002 — Interface server-side

### Decisão

Usar Django Templates + HTMX + Alpine.js.

### Motivos

- menor complexidade;
- manutenção mais simples;
- boa produtividade;
- adequado a workflow e formulários;
- reduz necessidade de SPA.

## ADR-003 — Oracle como banco principal

### Decisão

Usar Oracle Database 19c, conforme padrão definido.

### Restrições

- owner exclusivo;
- application user separado;
- sync user separado;
- Oracle Instant Client 19.28 disponível em `/opt/oracle/instantclient_19_28`;
- migrations revisadas;
- nada de acesso direto de escrita ao Senior.

## ADR-004 — Sincronização local de referências

### Estado

Substituída pela ADR-020 em 2026-07-27.

### Decisão

Não se aplica mais. A decisão inicial previa tabelas `REF_*` no SGPD.

### Motivos

- desempenho;
- independência temporária;
- isolamento;
- rastreabilidade;
- facilidade de snapshot;
- menor acoplamento.

## ADR-005 — Snapshot imutável

### Decisão

Copiar os dados do colaborador ao abrir o processo.

### Motivos

- preservar contexto histórico;
- evitar alteração retroativa;
- sustentar auditoria.

## ADR-006 — Templates versionados

### Decisão

Checklist e grupos serão versionados.

### Motivos

- processos antigos não podem mudar;
- auditoria;
- evolução segura.

## ADR-007 — Services para regras

### Decisão

Regras de negócio críticas serão implementadas em services explícitos.

### Motivos

- testabilidade;
- menor dependência de views;
- evitar signals ocultos;
- clareza.

## ADR-008 — Pendência como entidade

### Decisão

Pendências não serão apenas observações textuais.

### Motivos

- ciclo de vida;
- evidências;
- valores;
- decisões;
- relatórios;
- auditoria.

## ADR-009 — Valor como pretensão

### Decisão

Valores lançados por setores serão solicitações de análise.

### Motivos

- reduzir risco;
- permitir contestação;
- exigir aprovação;
- evitar desconto automático.

## ADR-010 — Processamento assíncrono

### Decisão

Notificações e escaladas serão assíncronas. Consultas cadastrais ao Senior são online e não usam sincronização.

## ADR-011 — Evidências fora do Oracle

### Decisão

Armazenar arquivos em storage dedicado e manter metadados no Oracle.

### Exceção

Somente usar BLOB se houver exigência técnica ou corporativa formal.

## ADR-012 — Liberação pelo DP

### Decisão

A liberação para rescisão é ação explícita do DP.

### Motivos

- responsabilidade funcional;
- controle;
- revisão humana;
- exceções.

## ADR-013 — Ambiente único DEV

### Decisão

Manter somente o ambiente DEV no escopo atual.

### Consequências

- não haverá configuração de HML ou PRD nesta fase;
- settings e documentação devem refletir apenas DEV;
- a criação futura de outro ambiente exigirá revisão de segurança, dados e implantação.

## ADR-014 — WhiteNoise sem Nginx

### Decisão

Usar WhiteNoise para servir arquivos estáticos do Django e não utilizar Nginx.

### Restrições

- WhiteNoise atende somente arquivos estáticos;
- evidências e uploads permanecem em storage separado e protegido;
- qualquer necessidade futura de proxy, TLS ou balanceamento exigirá nova decisão.

## ADR-015 — Redis sob demanda

### Decisão

Não manter Redis ativo nesta etapa. Quando uma funcionalidade exigir cache, fila ou lock distribuído, subir Redis em container no DEV.

### Consequências

- a fundação inicial não depende de Redis;
- a introdução do container deverá incluir health check, volume quando necessário e configuração reproduzível;
- worker assíncrono permanece adiado.

## ADR-016 — Sem CI/CD no escopo atual

### Decisão

Não implementar pipeline de CI/CD no ambiente DEV atual.

### Consequências

- testes, lint e validações serão executados localmente;
- os comandos de validação deverão ser documentados e reproduzíveis;
- a adoção futura de CI/CD exigirá nova decisão.

## ADR-017 — Secrets no `.env` do DEV

### Decisão

Manter usuário, senha e e-mail de integrações no arquivo `.env` local, nunca no repositório.

### Convenções

- usuários individuais seguem `nome.sobrenome`;
- senhas não seguem padrão previsível e não devem ser documentadas;
- `.env.example` contém somente nomes de variáveis e valores não sensíveis;
- o arquivo `.env` deve ter acesso restrito ao usuário da aplicação.

## ADR-018 — SMTP Microsoft 365

### Decisão

Usar Microsoft 365 SMTP com remetente `noreply@bsabioenergia.com.br`.

### Configuração

- host `smtp.office365.com`;
- porta 587;
- TLS/STARTTLS habilitado;
- usuário, senha e endereço do remetente definidos no `.env`.

### Validação pendente

Confirmar que SMTP AUTH está habilitado para a conta e que ela possui permissão de envio como o remetente configurado.

## ADR-019 — Evidências no filesystem local

### Decisão

Armazenar evidências no filesystem local privado do DEV.

### Restrições

- não servir evidências pelo WhiteNoise;
- não expor o diretório diretamente por URL;
- calcular SHA-256 e manter metadados no Oracle;
- restringir permissões no sistema operacional;
- definir backup, retenção e antivírus antes de armazenar dados reais.

## ADR-020 — Consulta direta ao Senior sem models

### Decisão

Consultar os objetos homologados de `VETORH` diretamente no Oracle por SQL `SELECT` parametrizado.

Não criar:

- models Django para tabelas ou views do Senior;
- models não gerenciados;
- tabelas locais `REF_*`;
- carga inicial, incremental ou reconciliação cadastral;
- views Oracle locais nesta etapa.

A view Django deverá delegar a consulta a um service/repository. Somente o snapshot criado na abertura do processo será persistido no SGPD.

### Motivos

- decisão funcional de consultar a fonte oficial em tempo real;
- objetos `VETORH` estão no mesmo serviço Oracle;
- grants `SELECT` já foram concedidos ao schema SGPD para o contrato inicial;
- elimina defasagem e operação de sincronização.

### Consequências

- maior acoplamento ao contrato físico do Senior;
- indisponibilidade do Senior impede novas pesquisas e snapshots;
- consultas exigem bind variables, paginação, timeout e testes de contrato;
- o usuário de runtime deve ser separado dos owners `SGPD` e `VETORH`;
- o snapshot do processo continua obrigatório e imutável.

## ADR-021 — Cadastro local de usuários e vinculação futura ao AD

### Decisão

Cadastrar no SGPD todos os usuários, gestores, e-mails, papéis e escopos.

O Senior HCM não será fonte de identidades ou autorizações. O MVP terá autenticação local. Em fase posterior, cada conta SGPD poderá ser vinculada a uma identidade do Active Directory para autenticação corporativa com uma única senha.

### Regras

- o perfil funcional continua pertencendo ao SGPD após a vinculação;
- a vinculação usa identificador corporativo estável e único, não apenas e-mail;
- uma identidade AD não pode ser vinculada a mais de uma conta SGPD;
- papéis e permissões não serão importados automaticamente do Senior;
- a senha local comum será desabilitada após ativar AD, mantendo apenas contingência administrativa controlada;
- local de trabalho não faz parte do cadastro nem das regras do MVP.

### Consequências

- gestor deverá ser selecionado entre usuários SGPD na abertura do processo;
- nome e e-mail do gestor serão preservados historicamente no processo;
- a indisponibilidade futura do AD não altera os dados cadastrais e de autorização mantidos no SGPD.
