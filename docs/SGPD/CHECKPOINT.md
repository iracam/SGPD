# Checkpoint Atual do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Ambiente: DEV único sobre Oracle 19c
- Fases estabilizadas: 1, 2, 2.5 e 2.7
- Fases em andamento: 3 — configuração funcional; 4 — workflow; 5 —
  pendências e evidências
- Próximo incremento: homologação funcional e visual da Fase 5
- Interface: SPA Angular 21; Django Admin técnico preservado
- Autorização: SuperAdmin global; `DP` atribuível; responsabilidade de setor
  derivada do vínculo vigente

## Baseline implementado

- fundação Django, Oracle, health checks e validações locais;
- autenticação local e integração AD configurável, com provisionamento
  explícito e contingência de SuperAdmin;
- contas, papel DP, escopos, setores e responsáveis auditados;
- consulta Senior somente leitura e cascata Empresa → Filial → Tipo →
  Colaborador;
- templates, perguntas e grupos versionados, com publicação imutável;
- abertura transacional em rascunho, snapshot e prevenção de duplicidade;
- seleção explícita de grupos e início idempotente;
- geração atômica de tarefas e snapshots de checklist;
- início, respostas simples e conclusão de tarefa com versão otimista, lock,
  idempotência e auditoria;
- pendências próprias com itens, comentários, regularização, classificação de
  bloqueio, concorrência, idempotência e auditoria;
- evidências privadas com validação de conteúdo, SHA-256, upload idempotente e
  download autorizado/auditado;
- hub de processos com abertura, rascunhos, processos em aberto e concluídos,
  além dos cards agrupados de tarefas ativas/concluídas.

## Estado corrente

O cadastro funcional básico está operacional. Regras automáticas de
aplicabilidade permanecem pendentes. O fluxo de processo cobre abertura,
seleção, início, tarefas e a primeira fatia vertical de pendências/evidências.
Itens `FILE` e com evidência obrigatória podem concluir depois do upload
privado. Pendência bloqueante aberta ou em regularização impede a conclusão da
tarefa.

O card `Em Aberto` reúne processos iniciados com ao menos uma tarefa não
concluída; ao concluir a última tarefa, o processo sai desse card e passa para
`Concluídos`. A transição formal `ENCERRADO`, prontidão e liberação ainda não
foram implementadas.

## Incremento autorizado implementado

Fase 5 — pendências e evidências:

- `SGPD_PENDING_ITEM`, `SGPD_PENDING_ITEM_LINE` e
  `SGPD_PENDING_COMMENT`, sem excluir histórico;
- comentários append-only e ciclo
  `ABERTA → EM_REGULARIZACAO → REGULARIZADA → ENCERRADA`;
- `SGPD_EVIDENCE` com arquivo fora do Oracle, metadados, SHA-256 e storage
  privado não servido pelo WhiteNoise;
- autorização de responsável vigente, `DP` no escopo e SuperAdmin, revalidada
  sob locks;
- bloqueio da conclusão por pendência bloqueante não regularizada ou evidência
  obrigatória ausente; a prontidão/liberação formal continua na Fase 8;
- services transacionais, versão otimista, idempotência, auditoria, API e SPA;
- cobertura de caminho feliz, negação, SuperAdmin, DP sem vínculo de setor,
  estado inválido, rollback de banco/arquivo, auditoria, versão concorrente,
  replay e dados incompletos.

## Restrições ativas

- nenhuma escrita em objetos internos do Senior;
- owner `SGPD` continua sendo a conexão única no DEV pela ADR-022;
- login AD só permanece ativo sob configuração homologada e CA válida quando
  TLS estiver selecionado;
- evidências não podem ser servidas pelo WhiteNoise;
- migrations exigem inspeção do SQL Oracle antes de aplicação;
- não antecipar desconto automático, encerramento ou liberação.

## Riscos e pendências relevantes

- conferir visualmente os painéis nos cinco breakpoints homologados;
- homologar regras automáticas de aplicabilidade;
- definir retenção operacional das evidências;
- homologar o limite de 10 MiB e o catálogo inicial PDF/PNG/JPEG;
- conferir visualmente pendências e upload nos cinco breakpoints homologados;
- paginação visual adicional dos painéis pode ser necessária com maior volume;
- o estado formal de encerramento e sua data aguardam a Fase 8.

## Baseline de qualidade

No incremento da Fase 5 passaram 337 testes backend e 75 frontend,
Ruff, formatação, Mypy, Django check, verificação de migrations e build Angular.
O SQL Oracle das migrations `offboarding.0005`, `pending_items.0001` e
`evidence.0001` foi revisado e aplicado no Oracle DEV. As quatro novas tabelas,
49 constraints e todos os índices estão válidos; o plano final está vazio.
Cada nova mudança deve executar o subconjunto pertinente e justificar qualquer
validação omitida.

O replay idempotente de pendências/evidências materializa consultas
`select_for_update()` sem paginação, devido à incompatibilidade do Oracle com
`FOR UPDATE` combinado a `FETCH FIRST`. A regressão foi validada também por
consulta bloqueada somente leitura no Oracle DEV.

## Histórico

O registro integral até 2026-07-30 está em
`history/checkpoints/2026-07.md`. O plano concluído de migração da SPA está em
`history/completed-plans/MIGRATION_FRONTEND_SPA.md`.
