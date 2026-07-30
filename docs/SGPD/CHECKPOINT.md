# Checkpoint Atual do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Ambiente: DEV único sobre Oracle 19c
- Fases estabilizadas: 1, 2, 2.5, 2.7 e 3
- Fases em andamento: 4 — workflow; 5 — pendências e evidências
- Próximo incremento: Fase 6 — valores e decisões segregadas
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

- homologar o limite de 10 MiB e o catálogo inicial PDF/PNG/JPEG;
- o expurgo de evidências é manual: a retenção de 5 anos está definida, mas não
  há rotina automática nem marco confiável de contagem enquanto a Fase 8 não
  fechar o encerramento formal;
- validar a retenção de 5 anos com Jurídico, RH e Segurança da Informação;
- paginação visual adicional dos painéis pode ser necessária com maior volume;
- o estado formal de encerramento e sua data aguardam a Fase 8;
- o DEV contém dados de homologação: processos `5bfc0d3a` (rascunho) e
  `9cbed216` (iniciado, com pendência bloqueante aberta), criados para exercitar
  as telas;
- o usuário `homolog.visual` permanece no DEV desativado e com senha
  inutilizável: a FK da auditoria append-only impede a exclusão;
- painel, setores e demais telas ainda não consomem o protocolo de conferência
  da ADR-047; aplicar a linguagem nos próximos incrementos de cada tela.

## Homologação funcional e visual das Fases 3 e 5

Concluída em 2026-07-30 sobre o Oracle DEV, com Chromium headless dirigido por
CDP nas cinco larguras homologadas (360, 480, 768, 1024 e 1440).

A regra `Regra Padrao` foi cadastrada e validada ponta a ponta: sem filtro, ela
é curinga, sugere `Grupo Padrão 01 - Todos` e o rascunho exibe a origem da
sugestão. A seleção continua explícita — o início permanece bloqueado até o
`DP` salvar, como especificado.

Foram fotografadas e conferidas painel, hub de processos, abertura, rascunho com
sugestão, tarefas expandidas com pendência e evidência, setores, editor de
regras, editor de template, editor de grupo e a pré-visualização do rascunho não
salvo. A varredura mediu overflow horizontal e erros de console em cada
combinação.

Dois defeitos foram encontrados e corrigidos:

- o textarea de comentário da pendência renderizava a string literal
  `undefined`, porque o binding indexava um `Record` sem entrada para pendência
  nova. Como comentário é append-only, um `Comentar` acidental gravaria lixo
  permanente na trilha. O tipo do signal passou a admitir `undefined` e o
  template ganhou a mesma guarda `?? ''` que as três ligações irmãs já tinham;
- `.metadados` estourava a largura em 768 e 1024 com as tarefas expandidas: o
  piso `repeat(3, minmax(8rem, 1fr))` não cabe nas duas colunas do painel em
  `md`. Passou a `minmax(0, 1fr)`, como os demais grids do arquivo.

A retenção operacional de evidências foi definida em 5 anos e registrada em
`SECURITY.md` §14.

## Identidade visual das telas de execução (ADR-047)

Em 2026-07-30, Minhas tarefas e Processos passaram a exercer a identidade que
já existia nos tokens: o protocolo de conferência. O vocabulário compartilhado
vive em `frontend/src/styles/_conferencia.scss` — grupos como seções com régua
e total em mono, chips de status sobre os tokens `--status-*` com rótulo
legível (enum cru não chega mais ao usuário), dado de registro em JetBrains
Mono e o trilho de conferência, cujo nó preenche em verdigris quando o item
está conferido. Tarefa concluída mostra a resposta registrada em texto, não
controles desabilitados vazios; o nível de bloqueio da pendência colore a
borda esquerda do cartão.

A homologação repetiu a varredura headless nas larguras homologadas, em tema
claro e escuro, com API simulada por interceptação para encenar os estados
(sem dependência de dados no Oracle DEV). Corrigiu-se no caminho a
sobreposição de colunas em `md`/`lg`: cartão de tarefa com `min-width: 0` e
linhas de ações com `flex-wrap`. Telas de execução novas devem consumir o
parcial; o texto normativo é a ADR-047.

## Baseline de qualidade

Na homologação das Fases 3 e 5 passaram 355 testes backend e 81 frontend — o
novo cobre a regressão do comentário e falha com `expected 'undefined' to be ''`
sem a correção —, além de Ruff, formatação, Mypy, Django check, verificação de
migrations e build Angular sem avisos. Nenhuma migration foi necessária: as
correções são de template, SCSS e tipo.

No incremento da identidade visual (ADR-047) os 81 testes frontend seguem
passando e o build Angular está sem avisos; não há mudança de backend. A
varredura headless não mediu rolagem horizontal nem erro de console em
360/768/1024/1440, claro e escuro.

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
