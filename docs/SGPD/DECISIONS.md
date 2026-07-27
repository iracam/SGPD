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

Usar Oracle, conforme padrão definido.

### Restrições

- owner exclusivo;
- application user separado;
- sync user separado;
- migrations revisadas;
- nada de acesso direto de escrita ao Senior.

## ADR-004 — Sincronização local de referências

### Decisão

Manter tabelas `REF_*` no SGPD.

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

Notificações, sincronizações e escaladas serão assíncronas.

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
