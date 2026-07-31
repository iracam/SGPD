# Checkpoint Atual do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Ambiente: DEV único sobre Oracle 19c
- Fases estabilizadas: 1, 2, 2.5, 2.7 e 3
- Fases em andamento: 4 — workflow; 5 — pendências e evidências; 6 — valores e
  decisões
- Próximo incremento: **Fase 6, fatia 5** — consolidação de valores por
  processo
- Interface: SPA Angular 21; Django Admin técnico preservado
- Autorização: SuperAdmin global; `DP` atribuível; responsabilidade de setor
  derivada do vínculo vigente; segregação de valores pela ADR-048

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
  configuração;
- nova versão de grupo de validação clonada da versão publicada e exclusão
  auditada de rascunhos de template e de grupo;
- protocolo de conferência da ADR-047 exercido por todas as telas da SPA, com
  cabeçalho de página global e selo de domínio.

## Estado corrente

A configuração funcional está completa: setores, responsáveis, templates,
grupos versionados e regras de aplicabilidade. A regra sugere e não aplica —
o rascunho pré-marca os grupos sugeridos e a seleção só existe depois que o
`DP` confirma e salva. Sem regra cadastrada, a seleção manual anterior
permanece inalterada. O fluxo de processo cobre abertura, seleção, início,
tarefas e a primeira fatia vertical de pendências/evidências.
Itens `FILE` e com evidência obrigatória podem concluir depois do upload
privado. Pendência bloqueante aberta ou em regularização impede a conclusão da
tarefa; a bloqueante até decisão só libera com a pretensão decidida ou a
pendência encerrada. A pendência de valor percorre informar → apurar →
contestar → decidir pela própria SPA, e o valor processado continua vazio até
que o Senior o registre.

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
- não antecipar desconto automático, encerramento ou liberação;
- valor é pretensão sujeita a análise (ADR-009): o SGPD nunca aplica desconto,
  e `VALOR_PROCESSADO` só é preenchido a partir do registro do Senior.

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
- a extensão da ADR-047 e os incrementos de edição de configuração de
  2026-07-31 foram conferidos por build e testes, mas ainda não passaram por
  varredura headless nas cinco larguras homologadas;
- a ADR-048 aceita, por decisão explícita, que o SuperAdmin decida a pretensão
  que ele mesmo informou; o risco correspondente é o R62 e a auditoria é a
  única evidência do rompimento;
- encerrar a pendência pelo endpoint genérico continua liberando a tarefa sem
  decisão de valor: é ato explícito, auditado e necessário para a pendência que
  nunca teve pretensão, mas contorna o guard e deve ser revisto na prontidão da
  Fase 8;
- a SPA do eixo de valor ainda não passou por varredura headless nas cinco
  larguras homologadas nem por exercício funcional no Oracle DEV; a conferência
  até aqui é de testes e build.

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

Em 2026-07-31 a linguagem alcançou o restante da SPA: painel, setores,
colaboradores, rascunho do processo, catálogo de workflow, auditoria e
usuários. `p-tag` saiu de todas as telas — o chip do parcial é o único desenho
de status de domínio — e nenhum enum cru (`USER_CREATED`, `GLOBAL`, `DP`,
`COMPANY`, `PUBLISHED`) chega mais ao usuário. O trio selo/título/lead e as
ações de página subiram para `styles.scss` como vocabulário global, junto com
a correção do `.lista-tabela`, cujos descendentes absolutos `.sr-only`
esticavam o body além do viewport (ADR-028). A ADR-047 foi estendida na mesma
data para registrar esse alcance.

## Fase 6 — valores e decisões (em andamento)

A fase foi fatiada em cinco: modelo, services, guard de bloqueio, API/SPA e
consolidação. **As fatias 1 a 4 estão implementadas; falta a fatia 5.**

Fatia 1 — modelo, migration `pending_items.0002`, aplicada no Oracle DEV:

- `SGPD_PENDING_AMOUNT` 1:1 com a pendência, com os cinco montantes do RF-026,
  moeda, justificativa, `informed_by`, aprovador e versão otimista;
- `SGPD_PENDING_DECISION` append-only, com parecer, decisor e
  `segregation_override`;
- categoria `VALOR`, os cinco estados do eixo de decisão e a classificação
  `BLOQUEANTE_ATE_DECISAO`, que não cabia em `VARCHAR2(20)` — a coluna foi
  alargada para 24, metadado no Oracle, sem rewrite.

Fatia 2 — quatro services transacionais, migration `offboarding.0007`
(`sqlmigrate` no-op) aplicada:

- `RegisterPendingAmountService` exige pendência `VALOR` aberta em setor com
  `allows_amount` — campo que existe desde a Fase 3 e até aqui nenhuma regra
  lia;
- `AssessPendingAmountService`, `ContestPendingAmountService` e
  `DecidePendingAmountService` completam o eixo; a decisão é append-only e
  resolve o valor aprovado em zero quando rejeitada ou abonada;
- segregação da ADR-048: apurar e decidir exigem `DP` vigente no escopo; quem
  informou não decide; o SuperAdmin decide sem barreira e a trilha grava
  `segregation_override`;
- o eixo de decisão não é alcançável pelo endpoint genérico de situação, que só
  lhe dá saída para o encerramento.

Fatia 3 — guard de bloqueio, sem migration:

- `BLOCKING_RELEASE_STATUSES` e `unresolved_blocking_q()`
  (`apps/pending_items/models.py`) passaram a ser a fonte única de quais
  situações liberam cada classificação; `BLOQUEANTE` continua se satisfazendo
  com `REGULARIZADA`/`ENCERRADA` e `BLOQUEANTE_ATE_DECISAO` só cede a
  `DECIDED_STATUSES`;
- `CompleteSectorTaskService` consulta as duas classificações numa única
  passagem e responde com a mensagem da classificação encontrada — regularizar
  não libera uma pendência bloqueante até decisão;
- a SPA passou a nomear a classificação nova e as cinco situações do eixo de
  valor (`_conferencia.scss`, ADR-047): sem isso, uma pendência criada pela API
  já renderizava rótulo vazio. O `select` de registro continua oferecendo só
  `BLOQUEANTE` e `NAO_BLOQUEANTE`, porque a tela de decisão é da fatia 4;
- `PendenciaTransicao` fixa no tipo que o endpoint genérico de situação não
  alcança o eixo de decisão.

Fatia 4 — API e SPA do eixo de valor, sem migration:

- quatro rotas sob `pending-items/<uuid>/amount/` (informar, `assessment/`,
  `contestation/`, `decision/`), todas com `Idempotency-Key`, versão otimista e
  resposta com a pendência inteira; o serializer da decisão exige valor
  aprovado só na aprovação de cobrança e o recusa na rejeição e no abono;
- a negativa da ADR-048 volta como 403 com o motivo legível — as views de valor
  tratam `PermissionDenied` localmente, porque o handler global responde
  mensagem genérica e aqui a barra é regra de negócio, não sonda de existência;
- o payload da pendência ganhou `amount` (cinco montantes, moeda, quem
  informou, quem aprovou e as decisões) e `can_analyse_amount`, que
  `can_analyse_amounts()` calcula com memo por processo; a tarefa passou a
  publicar `sector.allows_amount`, leitura viva da mesma coluna que o service
  consulta;
- em `Minhas tarefas`, a pendência de valor mostra o quadro de conferência em
  mono, as decisões com autor e a marca de `segregation_override`, e oferece
  informar, apurar, contestar e decidir conforme o estado e a capacidade. O
  formulário de registro passou a oferecer a categoria `Valor` e a
  classificação `Bloqueante até decisão`, que a fatia 3 deixou de fora por não
  haver caminho de decisão.

Falta a fatia 5: consolidação de valores por processo, com separação das
decisões marcadas por `segregation_override` para conferência posterior.

## Ciclo de vida do rascunho na configuração (2026-07-31)

O editor de configuração fechou o ciclo de vida das versões:

- `Nova versão` de grupo de validação clona a versão publicada e repica cada
  setor para a versão vigente do seu template, abrindo o rascunho para edição;
  `CreateValidationGroupVersionService` guarda rascunho único, em paridade com
  templates;
- rascunhos de template e de grupo podem ser excluídos por `DELETE` na rota da
  versão, com auditoria `TPL_DRAFT_DELETED` / `GROUP_DRAFT_DELETED`; versões
  publicadas continuam imutáveis e o rascunho inicial é indelével, como o
  cabeçalho;
- as pré-visualizações passaram a espelhar `Minhas tarefas`: um cartão por
  setor, prazo efetivo na mesma precedência do backend e checklist com os
  controles reais.

`templates_engine.0007` apenas amplia as opções de `EVENT_TYPE`: o
`sqlmigrate` é `(no-op)` e a migration está aplicada no Oracle DEV.

## Baseline de qualidade

Na fatia 4 a validação padrão foi executada por inteiro: 381 testes backend e
89 frontend, Ruff, formatação, Mypy, Django check, verificação de migrations e
build Angular sem avisos. Nenhuma migration foi necessária. Os quatro testes
backend novos exercem o ciclo pela API com trilha e replay, o 403 da
segregação e o 403 de quem responde pelo setor sem `DP`, o 409 de chave
reusada com corpo diferente, os dois erros de contrato da decisão e o payload
de tarefa com `allows_amount` e pretensão. Os cinco do frontend cobrem o envio
com versão e chave, a decisão sem valor aprovado, a ausência das ações para
quem não pode analisar, a presença delas para o `DP` e a leitura da decisão
com a marca de segregação.

Na fatia 3 a validação padrão foi executada por inteiro: 377 testes backend e
84 frontend, Ruff, formatação, Mypy em 169 arquivos, Django check, verificação
de migrations e build Angular sem avisos. Nenhuma migration foi necessária — o
guard só acrescenta constantes e uma `Q` ao módulo de models. Os quatro testes
novos cobrem a tarefa travada com a pretensão informada e liberada por
aprovação e por abono, a regularização que não libera, o encerramento que
libera e a pendência de valor não bloqueante que nunca travou. O teste do
frontend garante o rótulo da classificação nova e das situações do eixo de
valor.

Nas fatias 1 e 2 da Fase 6 passaram 373 testes backend, Ruff, formatação, Mypy
em 169 arquivos, Django check e verificação de migrations. Não houve mudança de
frontend. Os 15 testes novos cobrem o ciclo informado → apurado → contestado →
aprovado com trilha, rejeição e abono em zero, setor sem `allows_amount`,
categoria errada, autoaprovação negada, override do SuperAdmin com marca,
responsável de setor sem `DP` barrado, replay idempotente, versão obsoleta,
atalho pelo endpoint genérico e dupla decisão.

Em 2026-07-31 a validação padrão foi executada por inteiro: 358 testes backend
e 83 frontend, Ruff, formatação, Mypy, Django check, verificação de migrations
e build Angular sem avisos. A verificação encontrou dois arquivos fora do
formato — `templates_engine/services.py` e a migration `0007` — remanescentes
dos incrementos de exclusão de rascunho; foram formatados sem mudança de
comportamento. A varredura headless de largura ainda não foi repetida sobre
essas telas.

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
