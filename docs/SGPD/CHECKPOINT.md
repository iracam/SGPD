# Checkpoint Atual do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Ambiente: DEV único sobre Oracle 19c
- Fases estabilizadas: 1, 2, 2.5, 2.7 e 3
- Fases em andamento: 4 — workflow; 5 — pendências e evidências
- Próximo incremento: homologação funcional e visual das Fases 3 e 5
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
- regras de aplicabilidade que sugerem grupos pelo snapshot, com prioridade,
  validade, versão otimista e auditoria;
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
  além dos cards agrupados de tarefas ativas/concluídas;
- identificação cadastral legível na cascata: empresa rotulada pela razão
  social e filial pelo nome próprio (`R030FIL.NOMFIL`);
- pré-visualização do rascunho não salvo de template e de grupo no editor de
  configuração.

## Estado corrente

A configuração funcional está completa: setores, responsáveis, templates,
grupos versionados e regras de aplicabilidade. A regra sugere e não aplica —
o rascunho pré-marca os grupos sugeridos e a seleção só existe depois que o
`DP` confirma e salva. Sem regra cadastrada, a seleção manual anterior
permanece inalterada. O fluxo de processo cobre abertura, seleção, início,
tarefas e a primeira fatia vertical de pendências/evidências.
Itens `FILE` e com evidência obrigatória podem concluir depois do upload
privado. Pendência bloqueante aberta ou em regularização impede a conclusão da
tarefa.

O card `Em Aberto` reúne processos iniciados com ao menos uma tarefa não
concluída; ao concluir a última tarefa, o processo sai desse card e passa para
`Concluídos`. A transição formal `ENCERRADO`, prontidão e liberação ainda não
foram implementadas.

## Incremento autorizado implementado

Fase 3 — regras de aplicabilidade (RF-012, ADR-046):

- `SGPD_GROUP_APPLICAB_RULE` com seis campos de match opcionais, prioridade,
  situação e janela de validade;
- campo vazio é curinga; campo preenchido exige igualdade com o snapshot;
- união entre regras vigentes, sem supressão por prioridade;
- sugestão limitada aos grupos disponíveis pelo escopo do setor e resolvida
  para a versão publicada vigente;
- `applicability_suggestion` no rascunho, com a regra de origem de cada grupo;
- API e SPA de manutenção sob `manage_workflow_configuration`, com versão
  otimista, auditoria append-only e inativação em vez de exclusão.

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

Contrato Senior — legibilidade cadastral:

- `listar_empresas` passou a projetar a razão social da menor filial da empresa
  (`MIN(RAZSOC) KEEP (DENSE_RANK FIRST ORDER BY CODFIL)`), já que o Senior não
  possui nome de empresa próprio;
- filial, listagem e detalhe de colaborador passaram de `RAZSOC` para `NOMFIL`;
  o campo `FILIAL_NOME` do snapshot agora guarda o nome da filial, e
  `offboarding.0006` só ajusta o `verbose_name` correspondente;
- snapshots anteriores a essa mudança preservam a razão social gravada na
  abertura e não são reescritos.

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
- cadastrar e homologar o catálogo de regras de aplicabilidade, cuja tabela
  está criada e vazia no Oracle DEV;
- conferir visualmente o editor de regras e o bloco de sugestão do rascunho
  nos cinco breakpoints homologados;
- definir retenção operacional das evidências;
- homologar o limite de 10 MiB e o catálogo inicial PDF/PNG/JPEG;
- conferir visualmente pendências e upload nos cinco breakpoints homologados;
- conferir visualmente a pré-visualização de template/grupo nos cinco
  breakpoints homologados;
- paginação visual adicional dos painéis pode ser necessária com maior volume;
- o estado formal de encerramento e sua data aguardam a Fase 8.

## Baseline de qualidade

No incremento de legibilidade cadastral passaram 355 testes backend e 80
frontend, Ruff, formatação, Mypy, Django check, verificação de migrations e
build Angular. O `sqlmigrate` de `offboarding.0006` é `(no-op)` — só altera
metadados Django — e foi aplicado no Oracle DEV. As cinco consultas alteradas
do contrato Senior foram executadas somente leitura contra o Oracle DEV pelo
próprio `SeniorRepository`, retornando razão social por empresa e `NOMFIL` em
filial, listagem e detalhe.

No incremento das regras de aplicabilidade passaram os mesmos gates. O SQL
Oracle de
`templates_engine.0006_add_group_applicability_rules` foi revisado e aplicado
no Oracle DEV: a migration é aditiva, cria uma tabela, uma FK `PROTECT`, um
índice e três check constraints, todos dentro do limite de 30 caracteres do
Oracle, e a alteração de opções do `EVENT_TYPE` é no-op. A verificação somente
leitura confirmou 20 constraints e 3 índices `ENABLED`/`VALIDATED`, com a
tabela ainda vazia.

No incremento anterior, da Fase 5, o SQL das migrations `offboarding.0005`,
`pending_items.0001` e `evidence.0001` foi revisado e aplicado no Oracle DEV;
as quatro tabelas, 49 constraints e todos os índices estão válidos, com plano
final vazio. Cada nova mudança deve executar o subconjunto pertinente e
justificar qualquer validação omitida.

O replay idempotente de pendências/evidências materializa consultas
`select_for_update()` sem paginação, devido à incompatibilidade do Oracle com
`FOR UPDATE` combinado a `FETCH FIRST`. A regressão foi validada também por
consulta bloqueada somente leitura no Oracle DEV.

## Histórico

O registro integral até 2026-07-30 está em
`history/checkpoints/2026-07.md`. O plano concluído de migração da SPA está em
`history/completed-plans/MIGRATION_FRONTEND_SPA.md`.
