# Checkpoint Atual do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Ambiente: DEV único sobre Oracle 19c
- Fases estabilizadas: 1, 2, 2.5, 2.7, 3, 6, 7, 8 e **9 — implementada e
  homologada no Oracle DEV em 2026-08-01**
- Fases em andamento: 4 — workflow; 5 — pendências e evidências
- Publicação: `https://sgpd.bsabioenergia.com.br` por proxy em outro host desde
  2026-08-03; a aplicação sobe com `config.settings.production` (ADR-052)
- Em andamento: os cinco papéis funcionais atribuíveis — fatia 1 implementada,
  com a migration `accounts.0011` **ainda não aplicada no Oracle DEV**
- Próximo incremento: fatia 2 dos papéis (atribuição exclusiva do SuperAdmin);
  fora do repositório, rotacionar as senhas fracas do Oracle e do SMTP e trocar
  o bind do AD por conta de serviço com TLS (riscos R66 e R67); validar backup e
  restauração com o DBA (`RUNBOOK.md` §6)
- Configuração técnica: LDAP e e-mail administrados na central por SuperAdmin;
  o `.env` é baseline do primeiro boot (ADR-031, ADR-050)
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
  cabeçalho de página global e selo de domínio;
- notificações por e-mail com outbox no Oracle, varredura de prazos, escaladas,
  painel de falhas e reprocessamento auditado;
- central de configuração de e-mail: transporte SMTP, remetente, URL base, ritmo
  da fila e marcos de lembrete editáveis por SuperAdmin, com prova de envio;
- indicadores do painel, relatórios por período, exportação CSV auditada e sonda
  de operação, todos somente leitura em `apps/reporting`;
- manuais operacionais em `docs/operacao/` — responsável de área, Departamento
  Pessoal e configuração —, gerados de `.md` para HTML e PDF por
  `docs/operacao/build.mjs` e servidos em `/ajuda/<slug>/` atrás da sessão, com
  botão **Ajuda** em Minhas tarefas, Processos e Grupos e templates (ADR-053).

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
`Concluídos`. O ciclo formal — prontidão, liberação, processamento declarado,
encerramento, cancelamento e reabertura — está operacional ponta a ponta pela
tela `/fe/processos/:uuid/encerramento`, homologado no Oracle DEV, e o processo
cancelado tem card próprio no hub.

As notificações saem por e-mail a partir de uma fila no Oracle. Nada é enviado
dentro da requisição: o início do processo, a pendência bloqueante e o eixo de
valor gravam a mensagem na mesma transação do fato, e dois comandos agendados
varrem prazos e despacham. Sem agendamento instalado, a fila acumula em
`PENDENTE` e ninguém é avisado — é o risco R63 e a primeira pendência
operacional da fase.

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
- não antecipar desconto automático; liberação e encerramento existem apenas
  como ato humano explícito, nunca como consequência automática de estado;
- e-mail de notificação não carrega nome do colaborador, CPF, valor nem
  parecer: o corpo diz o que fazer e onde, e o dado fica no sistema
  (`SECURITY.md` §13.1);
- valor é pretensão sujeita a análise (ADR-009): o SGPD nunca aplica desconto,
  e `VALOR_PROCESSADO` só é preenchido a partir do registro do Senior.

## Riscos e pendências relevantes

- homologar o limite de 10 MiB e o catálogo inicial PDF/PNG/JPEG;
- o expurgo de evidências é manual: a retenção de 5 anos está definida e o
  encerramento formal já dá o marco de contagem, mas não há rotina automática;
- validar a retenção de 5 anos com Jurídico, RH e Segurança da Informação;
- paginação visual adicional dos painéis pode ser necessária com maior volume;
- o DEV contém dados de homologação que não podem ser apagados (pendência é
  append-only): `5bfc0d3a` (rascunho), `8c5ff6bf` (iniciado), `9cbed216`
  (encerrado, com o ciclo formal percorrido duas vezes), `c8787348` (cancelado)
  e `d80327c7` (rascunho aberto para o mesmo colaborador do cancelado, prova de
  que a chave foi liberada); seis pendências, quatro pretensões decididas e uma
  aguardando decisão; Financeiro, Departamento Pessoal, Almoxarifado BSA e TI
  ficaram com `PERMITE_VALOR` ligado para exercitar o eixo;
- o usuário `homolog.visual` permanece no DEV desativado e com senha
  inutilizável: a FK da auditoria append-only impede a exclusão;
- setores, catálogo de workflow, auditoria, usuários e colaboradores receberam a
  ADR-047 em 2026-07-31 e foram conferidos por build e testes, mas a varredura
  headless de 2026-07-31 cobriu apenas painel, processos, tarefas e valores;
- a ADR-048 aceita, por decisão explícita, que o SuperAdmin decida a pretensão
  que ele mesmo informou; o risco correspondente é o R62 e a auditoria é a
  única evidência do rompimento;
- encerrar a pendência pelo endpoint genérico continua liberando a tarefa sem
  decisão de valor, e a prontidão da Fase 8 adotou a mesma régua
  (`DECIDED_STATUSES`): fechar a pendência também retira o impedimento da
  liberação. É ato explícito, auditado e necessário para a pendência que nunca
  teve pretensão — a revisão prevista terminou nessa escolha, não em um guard
  novo;
- o total por moeda soma o valor informado de toda pretensão, inclusive a
  rejeitada e a abonada; quem confere lê o aprovado para saber o que vira
  cobrança. Se o total informado passar a ser lido como cobrança pretendida,
  vale separar as decididas em zero;
- o agendamento das notificações foi instalado no DEV em 2026-08-01 e a sonda
  passou a acusar parada em trinta minutos (R63); o resíduo agora é o inverso —
  ninguém confere o log do `cron`, então a sonda é a única testemunha;
- a URL base continua vazia no DEV, então o link da mensagem sai relativo e não
  clicável; agora é preenchível em `/fe/configuracoes/email`, sem tocar no host;
- as 16 notificações entregues na homologação permanecem no DEV, mais a
  notificação da reabertura que ficou pendente desde 2026-07-31 19:41 por falta
  de agendamento: a fila é append-only e não pode ser apagada, como a auditoria
  e as pendências;
- as três exportações da homologação da Fase 9 deixaram três linhas permanentes
  em `SGPD_REPORT_EXPORT`, também append-only;
- a entrega da notificação é ao menos uma vez: se o processo morrer entre o
  envio SMTP e a confirmação no banco, a mensagem volta para a fila e pode
  chegar duplicada. Duplicar aviso é aceitável; perder aviso não é;
- marco de prazo sem destinatário — setor sem responsável vigente ou processo
  sem `DP` no escopo — é contado e registrado em log, mas ninguém é avisado
  automaticamente de que o aviso não saiu;
- constraint de campo anulável precisa admitir o nulo na condição: no Oracle a
  comparação com `NULL` derruba `full_clean()`. O restante do projeto já seguia
  esse idioma e a Fase 6 era a única exceção — nenhuma outra tabela ficou
  pendente dessa revisão;
- `CharField` anulável nunca volta como `None` no Oracle: o backend do Django
  devolve `''` para a coluna em NULL. Regra que testa ausência precisa usar
  `not valor`, não `valor is None`, sob pena de passar no SQLite e nunca valer
  no DEV. A varredura de 2026-07-31 encontrou uma única ocorrência
  (`ReopenProcessService`) e não há outra pendente.

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

## Fase 6 — valores e decisões (homologada)

A fase foi fatiada em cinco: modelo, services, guard de bloqueio, API/SPA e
consolidação. **As cinco fatias estão implementadas, comitadas e homologadas no
Oracle DEV em 2026-07-31**, com varredura headless nas cinco larguras.

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

Fatia 5 — consolidação por processo, somente leitura, sem migration:

- `consolidate_process_amounts()` (`apps/pending_items/services.py`) soma as
  pretensões **por moeda** — juntar moedas diferentes numa linha seria falso —,
  conta as que ainda aguardam decisão e separa as decisões com
  `segregation_override`, como a ADR-048 exige da conferência;
- `GET /api/v1/processes/<uuid>/amounts/` mora na rota de processo e a view no
  app dono do dado; a visibilidade é a de `processes_for_actor`, então
  responsabilidade de setor recebe 404: a conferência é do escopo do processo;
- tela `/fe/processos/:uuid/valores` sobre o protocolo de conferência, com
  totais em mono, uma linha por pretensão com o setor de origem e a seção
  `Segregação rompida` destacada. A tela não decide nada — a decisão continua
  em `Minhas tarefas`, sob a segregação da ADR-048 — e o hub de processos ganhou
  o atalho `Conferir valores do processo` em cada processo expandido.

## Homologação da Fase 6 (2026-07-31)

O ciclo foi exercido pela própria API contra o Oracle DEV, autenticando cada
passo como o usuário real: nenhuma escrita direta em tabela.

A homologação encontrou um defeito que só existe no Oracle e travava o eixo
inteiro: as check constraints dos montantes comparavam `>= 0` sem admitir o
valor ausente. O Django valida constraints no banco em `full_clean()` e só
envolve a condição em `Coalesce(..., True)` onde `supports_comparing_boolean_expr`
é verdadeiro — no Oracle é falso, então `NULL >= 0` fica desconhecido e toda
pretensão ainda não apurada era recusada com quatro violações. A constraint do
banco nunca foi violada; o Oracle aceita a linha. A migration
`pending_items.0003` reescreve as cinco condições como `IS NULL OR >= 0`, o
idioma que as demais constraints anuláveis do projeto já usavam, e o teste novo
reproduz a falha no SQLite fixando o feature flag em falso.

Exercitado e conferido, com os dados permanecendo no DEV:

- ciclo completo informado → apurado → contestado → aprovado no Financeiro do
  processo `8c5ff6bf`, com 403 legível quando o responsável de setor tenta
  apurar;
- `DP` que informou tentando decidir a própria pretensão: 403 absoluto; outro
  `DP` decide e a rejeição resolve em zero;
- guard da fatia 3: a conclusão da tarefa foi recusada com “pendência de valor à
  espera da decisão” e liberada depois da decisão;
- SuperAdmin informando e decidindo sem barreira, com `segregation_override`
  gravado e destacado na conferência (ADR-048);
- pretensão em USD ao lado das de BRL, para exercitar o total por moeda;
- consolidação do processo com quatro pretensões, duas moedas e a seção
  `Segregação rompida`; responsável de setor recebe 404, como especificado.

A varredura headless cobriu Minhas tarefas, hub de processos, as duas telas de
valores e o painel, nas cinco larguras e nos dois temas — 50 combinações, sem
rolagem horizontal e sem erro de console.

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

## Homologação da Fase 7 (2026-07-31)

A fase foi exercida contra o Oracle DEV com envio real pelo Microsoft 365,
autorizado pelo responsável funcional: **16 e-mails entregues** aos
responsáveis de sete setores do processo `8c5ff6bf`, oito de
`TAREFA_A_VENCER` e oito de `TAREFA_VENCE_EM_BREVE`. As 16 tentativas fecharam
com sucesso na primeira, a fila terminou inteira em `ENVIADA` e nada ficou
pendente.

A homologação encontrou um defeito que só existe no Oracle e derrubava a
varredura: `_scan_processes` usava `distinct()` sobre `SGPD_OFFBOARDING_PROCESS`,
cujas colunas `REASON` e `NOTES` são NCLOB, e o Oracle recusa `SELECT DISTINCT`
sobre LOB com `ORA-00932`. O SQLite dos testes aceita, então a suíte passava
enquanto o comando quebrava na primeira execução real. A duplicidade do join
passou a morrer numa subconsulta (`processes_with_open_tasks()`), antes de
projetar as colunas, e o teste novo garante que a consulta não volte a pedir
`DISTINCT`.

A falha aconteceu **depois** da varredura das tarefas, que já havia enfileirado
as 16 mensagens: a execução seguinte não duplicou nada nem perdeu nada — a
chave de deduplicação absorveu as linhas existentes e o despacho as enviou. O
outbox provou o próprio desenho por acidente.

A varredura headless cobriu a tela `/fe/notificacoes` nas cinco larguras
homologadas e nos dois temas — 10 combinações, sem rolagem horizontal e sem
erro de console, com as 16 mensagens reais e o detalhe expandido. Um defeito
visual foi corrigido no caminho: o endereço do destinatário é uma palavra só e
atravessava a coluna vizinha em 360 sem esticar o documento, então a métrica de
overflow não o acusava; `.dados dd` ganhou `overflow-wrap: anywhere`.

Ficou aberto: `SGPD_BASE_URL` está vazio no `.env` do DEV, então os links das
mensagens saíram relativos (`/fe/tarefas`) e não são clicáveis no cliente de
e-mail. É configuração, não código — basta preencher a variável com a URL
externa do DEV antes do próximo envio.

## Central de configuração de e-mail (ADR-050)

Entre a Fase 7 e a Fase 8, por decisão explícita, a configuração de e-mail saiu
do `.env` para a central de `/fe/configuracoes`, no mesmo desenho que a ADR-031
deu ao LDAP. O card `E-mail e notificações` deixou de ser `Em breve`.

O singleton `SGPD_EMAIL_CONFIG` passou a governar transporte SMTP, remetente,
URL base dos links, ritmo da fila e os marcos de lembrete e escalada. O
`EMAIL_BACKEND` virou `ConfiguredEmailBackend`, que lê a configuração a cada
envio: mudar servidor, remetente ou marco não exige reinício. As variáveis do
`.env` continuam valendo como baseline enquanto o registro não existir — no DEV
ele ainda não existe, e a tela mostra `Origem efetiva: Ambiente`.

A central ganhou um interruptor de envio: desligado, a fila acumula em
`PENDENTE` e nada é entregue; religar despacha o acumulado sem perder mensagem.
A senha SMTP é cifrada como a de bind do LDAP e nunca volta pela API — campo em
branco preserva a vigente. A prova de envio vai obrigatoriamente para o endereço
da própria conta que pediu o teste.

A validação separa o que bloqueia do que apenas avisa: habilitar sem servidor ou
sem remetente é recusado; ausência de URL base, ausência de TLS e porta fora das
usuais são avisos que não impedem salvar.

O vocabulário visual da central virou o parcial `styles/_configuracao.scss`, e a
tela de LDAP passou a consumi-lo em vez de manter cópia — a varredura headless
repetiu as duas telas nas cinco larguras e nos dois temas, sem rolagem
horizontal, sem erro de console e sem diferença de aparência no LDAP.

Um defeito apareceu na própria suíte e foi corrigido antes do commit: a prova de
envio fixava o backend SMTP, então o teste abriu conexão viva com o Microsoft
365 e falhou com erro de autenticação real. A sonda passou a usar
`get_connection()` sem fixar backend — em produção é o dinâmico, nos testes é o
de memória. `config/settings/test.py` também passou a fixar o baseline de
e-mail, para que o resultado da suíte não dependa do `.env` da máquina.

## Baseline de qualidade

Na homologação da Fase 8 a validação padrão foi executada por inteiro: 457
testes backend e 106 frontend, Ruff, formatação, Mypy em 203 arquivos, Django
check, verificação de migrations e build Angular sem avisos. Nenhuma migration
foi necessária — os três defeitos são de regra calculada, idioma de leitura e
template. Os dois testes backend novos cobrem o item opcional deixado em branco
que não é inconsistência (com o item respondido sem evidência continuando a
impedir) e a reabertura que precisa retomar a chave quando ela chega como string
vazia — este falha com `assert '' == '1:2:1:321'` sem a correção. O teste novo
do frontend garante que o processo cancelado não exibe impedimento da liberação
nem o contador, preservando as contagens.

Na central de e-mail a validação padrão foi executada por inteiro: 423 testes
backend e 99 frontend, Ruff, formatação, Mypy em 196 arquivos, Django check,
verificação de migrations e build Angular sem avisos. As duas migrations foram
revisadas e aplicadas no Oracle DEV: `system_settings.0003` cria
`SGPD_EMAIL_CONFIG` com quatro check constraints próprias, todas
`ENABLED`/`VALIDATED` sobre tabela vazia, e `accounts.0010` é `(no-op)`, apenas
amplia as opções de `EVENT_TYPE`. Os 13 testes backend novos cobrem a
substituição do baseline pelo registro, a cifra do segredo e a preservação da
senha em branco, a trilha sem segredo, a barra de SuperAdmin na API e no
service, a versão obsoleta, a recusa de habilitar sem servidor ou remetente, a
separação entre erro e aviso, o payload que nunca devolve a senha, o contrato
dos marcos, a prova bem-sucedida e a recusada, a fila retida com o envio
desligado e o backend montado a partir do registro. Os quatro do frontend cobrem
a leitura da configuração vigente, o envio com versão e senha vazia, o aviso de
URL base e a prova de envio.

Na Fase 7 a validação padrão foi executada por inteiro: 410 testes backend e 95
frontend, Ruff, formatação, Mypy em 190 arquivos, Django check, verificação de
migrations e build Angular sem avisos. As duas migrations foram revisadas e
aplicadas no Oracle DEV: `notifications.0001` cria duas tabelas, dois índices
próprios e seis constraints — a verificação somente leitura confirmou 35
constraints `ENABLED`/`VALIDATED`, 15 índices `VALID` e as tabelas vazias —, e
`offboarding.0008` é `(no-op)`, apenas amplia as opções de `EVENT_TYPE`.

Os 26 testes backend novos cobrem a armadilha do `full_clean()` no Oracle, a
deduplicação do marco, a imutabilidade da fila, a tentativa aberta ou fechada
por inteiro, o envio com fechamento da tentativa, o backoff e a desistência, a
reabertura do que ficou preso em envio, os dois comandos, cada marco de prazo e
seus destinatários, o marco sem ninguém para avisar, o painel restrito ao
escopo, o reprocessamento com trilha e replay, a recusa da mensagem já entregue
e da versão obsoleta, os quatro gatilhos de domínio e a consulta de processos
que não pode pedir `DISTINCT` ao Oracle. Os três do frontend
cobrem a leitura da fila com o erro da última tentativa, o reprocessamento com
versão e chave, e a ausência da ação para mensagem entregue.

Dois defeitos apareceram na própria suíte e foram corrigidos antes do commit: a
janela de reabertura zerada era descartada por `or` — um `timedelta(0)` é falsy
— e o número da tentativa colidia depois do reprocessamento, porque reusava o
contador de orçamento em vez de continuar a numeração histórica. Os outros dois
— o `DISTINCT` sobre LOB e o endereço que atravessava a coluna — só apareceram
na homologação, e estão registrados na seção correspondente.

Na homologação da Fase 6 a validação padrão foi executada por inteiro: 384
testes backend e 92 frontend, Ruff, formatação, Mypy, Django check, verificação
de migrations e build Angular sem avisos. O teste novo fixa
`supports_comparing_boolean_expr` em falso e falha sem a correção com as quatro
violações que o Oracle produzia. O SQL de `pending_items.0003` foi revisado —
cinco `DROP CONSTRAINT` e cinco `ADD CONSTRAINT` sobre tabela vazia, nomes
dentro do limite de 30 caracteres — e aplicado no Oracle DEV; a verificação
somente leitura confirmou as seis check constraints `ENABLED`/`VALIDATED` com a
condição nova.

Na fatia 5 a validação padrão foi executada por inteiro: 383 testes backend e
92 frontend, Ruff, formatação, Mypy, Django check, verificação de migrations e
build Angular sem avisos. Nenhuma migration foi necessária — a consolidação é
leitura. Os dois testes backend novos cobrem o total por moeda com a decisão do
SuperAdmin separada e a consolidação que ignora pendência sem pretensão e
responde 404 a quem só responde pelo setor; os três do frontend cobrem a soma
exibida, a seção de segregação rompida e o processo sem pretensão.

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

## Fase 7 — notificações e escaladas

A fase foi fatiada em cinco, todas implementadas e comitadas em 2026-07-31. A
decisão de transporte está na **ADR-049**: a fila é a tabela `SGPD_NOTIFICATION`
no Oracle, gravada na mesma transação do fato que a origina, e o envio roda
fora da requisição por comando agendado. Redis, broker e worker ficaram fora —
nenhuma das três exigências da fase (histórico durável para o painel de falhas,
deduplicação da varredura, gravação na transação do domínio) é atendida por um
broker, e em todos os desenhos a tabela de outbox continuava necessária.
Nenhuma dependência nova entrou no projeto.

Fatia 1 — modelo, migration `notifications.0001`, aplicada no Oracle DEV:

- `SGPD_NOTIFICATION` com chave de deduplicação única, evento, canal,
  destinatário, endereço congelado, assunto e corpo, situação, tentativas,
  backoff, último erro e versão otimista;
- `SGPD_NOTIFICATION_ATTEMPT` append-only, aberta antes do envio e fechada uma
  única vez depois dele: é o que distingue “nunca tentou” de “tentou e o SMTP
  recusou”;
- as condições anuláveis já nasceram no idioma da Fase 6 (`IS NULL OR …`), e o
  teste correspondente fixa `supports_comparing_boolean_expr` em falso.

Fatia 2 — enfileiramento, mensagens e despacho, sem migration:

- `EnqueueNotificationService` roda dentro da transação de quem o chama; varrer
  o mesmo marco de novo é o caso normal e é resolvido por uma consulta, com o
  savepoint e a unicidade do banco como rede da corrida;
- nove templates em `apps/notifications/templates/notifications/`, um por
  evento, com a primeira linha como assunto e o rodapé compartilhado;
- `DispatchNotificationsService` toma cada mensagem sob lock, envia fora da
  transação e confirma depois; sem `FOR UPDATE` combinado a `FETCH FIRST`, como
  o Oracle exige. Backoff de 1 min a 1 h e desistência em `max_attempts`;
- comando `sgpd_dispatch_notifications`.

Fatia 3 — varredura de prazos, sem migration:

- os cinco marcos de `WORKFLOWS.md` §7, com janelas configuráveis por ambiente;
- destinatários por responsável vigente do setor, `DP` do escopo e setor de
  escalada; SuperAdmin não entra por autoridade global — receber todo atraso do
  sistema seria ruído, não visibilidade;
- comando `sgpd_scan_notifications`, com `--dispatch` para varrer e enviar na
  mesma execução.

Fatia 4 — painel de falhas e reprocessamento, migration `offboarding.0008`
(`sqlmigrate` no-op) aplicada:

- `GET /api/v1/notifications/` com resumo por situação e
  `POST …/<uuid>/reprocess/` com `Idempotency-Key`, versão otimista e evento
  `NOTIFICATION_REPROCESSED`;
- visibilidade de `processes_for_actor`: quem só responde por setor não alcança
  a fila, pela mesma régua da consolidação de valores;
- só a mensagem em `FALHA` volta para a fila — reenviar uma entregue duplicaria
  o e-mail. O reprocessamento zera o orçamento de tentativas sem apagar
  nenhuma: a numeração da tentativa é histórica e nunca se repete;
- tela `/fe/notificacoes` sobre o protocolo de conferência (ADR-047), com o
  resumo clicável, o erro da última tentativa e o corpo enviado.

Fatia 5 — gatilhos de domínio, sem migration:

- início do processo avisa cada setor da tarefa nova;
- pendência bloqueante avisa o `DP` do escopo; informativa e não bloqueante não
  geram aviso;
- pretensão informada e pretensão contestada avisam o `DP` de que há decisão
  pendente — a versão da pretensão entra na chave, então a contestação reabre o
  aviso;
- decisão avisa o setor que informou o valor.

## Fase 8 — prontidão, liberação e encerramento formal

A decisão que governa a fase é a **ADR-051**: o `STATUS` guarda somente estado
formal e a situação funcional é calculada a cada leitura. A fase foi fatiada em
quatro, todas implementadas e homologadas no Oracle DEV em 2026-07-31.

Fatia 1 — estados formais, marcas e migration `offboarding.0009`, aplicada no
Oracle DEV:

- `LIBERADO_PARA_RESCISAO`, `RESCISAO_PROCESSADA`, `ENCERRADO` e `CANCELADO`
  com data, ator e observação próprios, mais o número declarado da rescisão;
- `ACTIVE_EMPLOYEE_KEY` anulável: é liberada no encerramento e no cancelamento,
  e só neles;
- check constraints por ramo de estado, no idioma anulável que o Oracle exige.

Fatia 2 — prontidão calculada e as três transições do caminho feliz, sem
migration:

- `evaluate_process_readiness()` (`apps/offboarding/readiness.py`) resolve
  situação, impedimentos e avisos sobre tarefas, pendências e pretensões, sem
  gravar nada; a liberação a refaz sob lock, porque o que a tela leu não decide;
- liberar exige processo iniciado e prontidão; registrar o processamento exige
  processo liberado, número declarado e data nem futura nem anterior à
  liberação; encerrar exige rescisão processada e nenhuma pendência em curso;
- a liberação congela a tarefa mas não a pendência: sem isso o encerramento
  seria inalcançável.

Fatia 3 — cancelamento e reabertura, migrations `offboarding.0010` e
`notifications.0002` (ambas `sqlmigrate` no-op) aplicadas:

- `CancelProcessService` cancela as tarefas ainda abertas, libera a chave do
  colaborador, exige justificativa e alcança tanto o rascunho quanto o processo
  iniciado. É terminal: não há volta de `CANCELADO` (ADR-051);
- `ReopenProcessService` é exclusivo do SuperAdmin — a “permissão especial” do
  RF-032 é a autoridade global da ADR-044, e o `DP` que liberou não desfaz o
  próprio ato sozinho. A trilha grava o estado anterior inteiro
  (`WORKFLOWS.md` §8);
- reabrir devolve à análise as tarefas concluídas que o SuperAdmin indicar;
  lista vazia corrige só a marca formal, sem devolver trabalho ao setor;
- a reabertura retoma a chave do colaborador e é recusada quando outro processo
  já a tomou: quem arbitra é a unicidade do banco, não uma leitura prévia;
- dois eventos de notificação novos avisam o setor. A chave de deduplicação da
  reabertura carrega tarefa e ordem (`t<id>r<n>`): sem a tarefa, dois setores do
  mesmo responsável — ou dois processos reabertos pela primeira vez — colidiriam
  e o segundo aviso sumiria.

Fatia 4 — API e SPA do ciclo formal, sem migration:

- `GET …/readiness/` devolve estado formal, marcas de cada ato, situação
  recalculada, impedimentos da liberação, impedimentos do encerramento e as
  tarefas; cinco `POST` (`release`, `processing`, `close`, `cancel`, `reopen`)
  respondem a mesma leitura, com `expected_version`, `Idempotency-Key` e
  `idempotency_replayed`;
- a recusa por regra volta em `details` e a tela mostra o impedimento
  recalculado, não o rótulo genérico do envelope — é a informação que decide o
  que fazer em seguida. A negativa de autoridade volta 403 com o motivo
  legível, porque quem a recebe já enxerga o processo;
- `process_payload` ganhou o bloco `formal`, e a listagem passou a trazer os
  quatro atores das marcas no `select_related`: sem isso, cada linha custaria
  quatro consultas;
- tela `/fe/processos/:uuid/encerramento` sobre o protocolo de conferência
  (ADR-047), separando o chip do **estado formal** do chip da **situação
  calculada** — confundi-los anularia a ADR-051. Cada ato aparece conforme o
  estado; a liberação fica indisponível enquanto houver impedimento, e o
  encerramento enquanto houver pendência em curso;
- a reabertura só é oferecida ao SuperAdmin, com seleção das tarefas concluídas
  que voltam para análise; sem nenhuma marcada, corrige só a marca formal. A
  SPA orienta, a API decide;
- o hub ganhou o card `Cancelados` (`status=CANCELADO`) e o atalho
  `Conferir encerramento do processo`: sem card próprio, o cancelado sumiria do
  hub, já que não está em aberto nem entre os concluídos.

Na fatia 4 a validação padrão foi executada por inteiro: 455 testes backend e
105 frontend, Ruff, formatação, Mypy em 203 arquivos, Django check, verificação
de migrations e build Angular sem avisos. Nenhuma migration foi necessária — a
fatia é contrato e tela. Os 7 testes backend novos cobrem a leitura da situação
sem efeito colateral, o ciclo inteiro pela API com replay, a recusa por
impedimento, versão obsoleta e chave reusada, a data futura do processamento, o
cancelamento sem motivo e o processo cancelado achável só pelo filtro de
estado, o 403 legível da reabertura ao `DP` com a reabertura do SuperAdmin
devolvendo a tarefa, e o ciclo inteiro fora do alcance de quem não é `DP`. Os 6
do frontend cobrem a separação entre estado e situação com o botão travado, a
liberação com versão e chave, o impedimento recalculado exibido na recusa, o
cancelamento que exige motivo, a ausência da reabertura para quem não é
SuperAdmin e a reabertura com as tarefas escolhidas.

Na fatia 3 a validação padrão foi executada por inteiro: 448 testes backend e
99 frontend, Ruff, formatação, Mypy em 202 arquivos, Django check e verificação
de migrations. Não houve mudança de frontend, então o build Angular não foi
repetido. Os 13 testes novos cobrem o cancelamento com tarefa aberta, pendência
preservada e chave liberada, o aviso ao setor, o cancelamento do rascunho, as
recusas de motivo vazio, versão obsoleta e chave reusada, o cancelamento
inalcançável a partir do liberado, o responsável de setor sem `DP`, a
reabertura negada ao `DP`, a reabertura do encerrado com retomada da chave e
trilha do estado anterior, a reabertura sem tarefa, o segundo aviso da segunda
reabertura, as recusas de tarefa alheia e de tarefa não concluída, e a
reabertura barrada pela chave já tomada por outro processo.

## Homologação da Fase 8 (2026-07-31)

O ciclo foi exercido pela própria API contra o Oracle DEV, com a sessão do
usuário real em cada passo: nenhuma escrita direta em tabela. A varredura
headless cobriu a tela nova em seis estados formais — iniciado com impedimento,
pronto, liberado, rescisão processada, encerrado e cancelado — mais o hub, nas
cinco larguras homologadas e nos dois temas: **74 combinações, sem rolagem
horizontal e sem erro de console**.

A homologação encontrou três defeitos, todos corrigidos:

- **a prontidão exigia mais do que a conclusão da tarefa jamais exigiu.**
  `_validated_answers` aceita o item `FILE` opcional sem arquivo e o item comum
  com `requires_evidence` que o setor deixou em branco; `_checklist_inconsistencies`
  exigia evidência sempre que `requires_evidence` estivesse ligado. Um item
  opcional legitimamente vazio virava impedimento permanente, e o texto ainda o
  chamava de inconsistência crítica — que, por definição, só apareceria se o
  dado mudasse depois da conclusão. O processo `9cbed216`, com as nove tarefas
  concluídas, nunca poderia ser liberado. A régua da prontidão passou a ser a
  mesma da conclusão;
- **a reabertura nunca retomava a chave do colaborador no Oracle.** O Oracle
  guarda a chave liberada em NULL, mas o backend do Django devolve `''` ao ler
  um `CharField`: o `if process.active_employee_key is None` do
  `ReopenProcessService` é falso em toda leitura real. O processo voltava à
  ativa com a chave solta, e a unicidade do banco — a árbitra da ADR-051 —
  nunca era consultada, o que permitiria dois processos vivos para o mesmo
  colaborador. Passou a `if not …`. É a terceira armadilha Oracle-only da série
  (constraint anulável, `DISTINCT` sobre LOB, agora leitura de `CharField`);
- **a tela listava impedimento da liberação em estado terminal.** No processo
  cancelado, a prontidão exibia “O processo não possui tarefas de setor” com a
  marca vermelha e o contador, sobre um processo em que nada há a fazer.
  Impedimento e aviso passaram a aparecer só enquanto a liberação é alcançável;
  as contagens ficam, porque são conferência.

Exercitado e conferido, com os dados permanecendo no DEV:

- ciclo completo em `9cbed216`: pronto → liberado → rescisão processada →
  encerrado, com `DP` vigente no escopo, replay idempotente, 409 de chave
  reusada com corpo diferente e versão obsoleta recusada;
- recusas do processamento declarado: data futura, data anterior à liberação e
  número ausente; encerramento negado antes do processamento. Nenhuma delas
  alterou estado, versão ou chave;
- reabertura pelo SuperAdmin devolvendo Almoxarifado BSA à análise: chave
  retomada, marcas limpas, trilha com o estado anterior inteiro e a notificação
  `PROCESSO_REABERTO` enfileirada com a chave `t66r1:44`;
- **o ciclo formal refeito por inteiro depois da reabertura** — o setor concluiu
  de novo pela API, e liberação, processamento e encerramento correram outra
  vez até `v10`, confirmando a afirmação do `ReopenProcessService`;
- `403` legível para o responsável de setor sem `DP` e para o `DP` que tenta
  reabrir; a reabertura é exclusiva do SuperAdmin (ADR-044, ADR-051);
- cancelamento de um rascunho aberto para isso (`c8787348`): motivo exigido,
  chave liberada com `employee_key_released` na trilha, replay idempotente,
  reabertura do cancelado recusada — é terminal — e, como prova de que a chave
  saiu mesmo, um processo novo aberto para o mesmo colaborador (`d80327c7`);
- hub com os quatro cards povoados e o atalho `Conferir encerramento do
  processo` dentro do processo expandido.

Observação sem defeito: o `<input type="date">` do processamento aparece em
`MM/DD/AAAA` no Chromium headless porque o controle nativo segue a locale do
navegador, não a da página — o documento declara `lang="pt-BR"`.

## Fase 9 — relatórios e operação (2026-08-01)

A fase foi fatiada em quatro, todas implementadas e comitadas. O app novo
`apps/reporting` é somente leitura: nada nele decide, enfileira ou apaga. Todo
número é calculado na consulta, como a situação funcional da ADR-051 —
contador guardado envelhece e passa a mentir. A visibilidade não foi
reinventada: `processes_for_actor` e `sector_tasks_for_actor` são as mesmas
funções das listagens.

Fatia 1 — indicadores do painel (RF-034, RF-035), sem migration:

- `GET /api/v1/reporting/dashboard/` devolve dois blocos **por capacidade**:
  coordenação exige `DP` vigente ou autoridade global; setor exige enxergar ao
  menos uma tarefa. Sem bloco algum a resposta é `null` nos dois, não 403 — é
  informação, não negativa;
- as janelas de “próximo do prazo” vêm da mesma configuração que a varredura
  usa (`WORKFLOWS.md` §7): o painel e o e-mail não podem discordar sobre o que
  é urgente;
- o painel da SPA passou a exercer o protocolo de conferência (ADR-047), com o
  processo crítico levando à conferência do encerramento.

Fatia 2 — os oito relatórios do RF-036, sem migration:

- `GET /api/v1/reporting/reports/?start=&end=` com tempo médio do processo e
  por setor, pendências por categoria, processos por empresa, processos
  vencidos, setores com maior atraso, valores informados e aprovados e
  processos liberados por mês;
- duas naturezas convivem no mesmo recorte e o payload diz qual é qual: o
  período filtra o **fato ocorrido**, mas atraso não tem data própria —
  processo vencido e setor atrasado são a **fotografia de agora**. Fingir
  recorte esconderia atraso de quem confere;
- relatório é conferência do escopo do `DP`: quem só responde por setor recebe
  403, a mesma régua da consolidação de valores e da fila de notificações;
- tela `/fe/relatorios`, e o vocabulário dos números virou o parcial
  `styles/_indicadores.scss`, compartilhado com o painel.

Fatia 3 — exportação CSV auditada, migration `reporting.0001` aplicada no
Oracle DEV:

- `GET /api/v1/reporting/exports/{processos|tarefas|pendencias}.csv`, no mesmo
  recorte e na mesma visibilidade dos relatórios;
- `SGPD_REPORT_EXPORT` é append-only e guarda ator, conjunto, período, linhas e
  correlation ID. A trilha é gravada **antes** de os bytes saírem: download
  interrompido continua sendo acesso ao dado (`SECURITY.md` §13.3);
- o arquivo não leva CPF, motivo do desligamento, justificativa da pretensão
  nem parecer da decisão — texto de juízo e dado restrito se leem no sistema,
  onde o acesso é auditado linha a linha;
- recorte acima de 5000 linhas é recusado com mensagem legível, em vez de
  arquivo truncado: quem confere somaria o que não é o total.

Fatia 4 — operação e runbook, sem migration:

- `GET /api/v1/reporting/operations/` e tela `/fe/operacao`, exclusivas do
  SuperAdmin, com fila por situação, pendente mais antiga, último envio,
  ocupação das evidências e contagem da retenção;
- o veredito da fila é deliberadamente simples: pendente além da tolerância
  significa que ninguém despachou. Não há heartbeat do agendador — inventar um
  seria mais uma coisa para parar em silêncio; a própria fila é a evidência;
- comando `sgpd_operations_check`, com `--quiet` e saída 1 quando a fila está
  parada, para o agendador ou um monitor externo reclamarem sem tela (R63);
- `RUNBOOK.md` novo: rotina diária, agendamento, sintomas e reação, e-mail,
  exportações, evidências e retenção, backup e restauração, saúde, migrations,
  armadilhas do Oracle já pagas e roteiro de treinamento.

### Armadilhas do Oracle observadas na fase

Todas passariam pelo SQLite dos testes sem reclamar, como o `DISTINCT` sobre
LOB da Fase 7:

- **`AVG` sobre `INTERVAL DAY TO SECOND` é `ORA-00932`** — a subtração de dois
  `TIMESTAMP` no Oracle é intervalo, e `AVG` não o aceita. Toda média de
  duração é calculada em Python, sobre a projeção dos dois instantes;
- **`GROUP BY` não aceita LOB** — `annotate(Count(...))` sobre o processo
  levaria `REASON`/`NOTES` ao agrupamento. As contagens saem de consultas
  próprias, agrupadas pela chave, e se juntam em Python;
- nenhum agrupamento recai sobre queryset anotado com `Exists`, que levaria a
  anotação ao `GROUP BY`.

Dois testes novos fixam as duas primeiras como regressão.

### Baseline de qualidade da fase

Validação padrão por inteiro: 484 testes backend e 119 frontend, Ruff,
formatação, Mypy em 219 arquivos, Django check, verificação de migrations e
build Angular sem avisos. A única migration da fase, `reporting.0001`, foi
revisada e aplicada no Oracle DEV — uma tabela, uma FK `PROTECT` sem índice
redundante, duas check constraints nomeadas e um índice; a verificação somente
leitura confirmou 13 constraints `ENABLED`/`VALIDATED`, índice `VALID` e tabela
vazia.

A validação foi reexecutada por inteiro em 2026-08-01, depois dos commits de
documentação e do agendamento, com a árvore de trabalho limpa: os mesmos 484
testes backend e 119 frontend, Ruff, formatação (245 arquivos), Mypy nos mesmos
219 arquivos, Django check, `makemigrations --check` sem alteração pendente e
build Angular sem avisos. Nenhum número mudou — esses commits não tocam em
código.

## Homologação da Fase 9 (2026-08-01)

Exercida pela própria API contra o Oracle DEV, com a sessão de cada usuário
real: `macari` (DP global e responsável de TI), `fernando.martins` (só
responsável de setor) e `admin` (SuperAdmin). Nenhuma escrita direta em tabela.

Conferido, com os dados permanecendo no DEV:

- painel do `DP` com os cinco processos do DEV: 1 em aberto, 1 concluído, 2
  rascunhos, 1 cancelado, nenhum vencido — e `SILVINO CARLOS ALVES` como
  processo crítico com 7 tarefas vencidas. **Processo vencido e tarefa vencida
  são perguntas diferentes**: a data limite do processo é 2026-08-07 e ainda
  não passou, enquanto as tarefas, de SLA em horas, venceram;
- pendências abertas, bloqueantes e valores aguardando decisão em zero, o que
  confere com o banco: as sete pendências do DEV estão todas regularizadas ou
  decididas;
- quem só responde por setor recebe o bloco de setor e `null` na coordenação;
- relatórios na janela padrão: ciclo médio de 1,1 dia sobre o processo
  encerrado, nove setores no tempo médio, 6 pendências de valor e 1 de
  equipamento, duas empresas, dois totais por moeda (BRL 2.720,00 informado com
  BRL 990,00 aprovado; USD 150,00) e 1 liberação em jul/2026;
- **período de 2020 esvazia o fato e preserva a fotografia**: empresas e
  pendências vazias, sete setores atrasados intactos — a distinção do desenho
  provada com dado real;
- as três exportações com BOM, `;`, decimal com vírgula e data pt-BR: 5
  processos, 18 tarefas e 7 pendências, cada uma com sua linha na trilha
  `SGPD_REPORT_EXPORT` (ator, período, linhas e correlation ID). Nenhum
  cabeçalho com CPF, justificativa ou parecer; recorte grande demais recusado
  em 400 sem gravar trilha;
- 403 legível para o responsável de setor nos relatórios e na exportação, 403
  para o `DP` na sonda de operação, 404 para conjunto desconhecido e 400 no
  período invertido;
- **a sonda encontrou o R63 em campo**: a fila do DEV tem 16 enviadas e 1
  pendente desde 2026-07-31 19:41 — a notificação da reabertura da Fase 8, que
  nunca foi despachada porque o agendamento não está instalado. O veredito saiu
  exatamente como projetado.

A varredura headless cobriu painel, relatórios e operação nas cinco larguras e
nos dois temas — **30 combinações, sem rolagem horizontal e sem erro de
console**. Três acabamentos foram corrigidos no caminho:

- o veredito da fila aparecia duas vezes na tela parada, no aviso e na nota
  abaixo dos dados; a nota passou a existir só quando não há problema;
- a mensagem do veredito trazia crase de Markdown e apontava para
  `ENVIRONMENT.md` §3, de onde o procedimento saiu; virou texto puro apontando
  o `RUNBOOK.md`, porque ela é lida na tela e no log do agendador, e nenhum dos
  dois interpreta marcação;
- datas em prosa saíam em ISO no painel e nos relatórios; passaram a
  `dd/MM/yyyy`. O `<input type="date">` continua em `MM/DD/AAAA` no Chromium
  headless — o controle nativo segue a locale do navegador, não a da página,
  como já observado na Fase 8.

## Agendamento instalado no DEV (2026-08-01)

Autorizado explicitamente e instalado no `crontab` do usuário da aplicação:
varredura com despacho a cada dez minutos e sonda a cada trinta. As entradas
estão no `RUNBOOK.md` §2, com caminho absoluto do `uv` e `cd` explícito — o
`cron` roda a partir do `HOME` e com `PATH` mínimo, e sem isso `uv run
manage.py` falha com `Failed to spawn`.

A primeira execução fez o que estava represado desde a Fase 8: **23 e-mails
reais saíram** para dez destinatários da empresa — a notificação
`PROCESSO_REABERTO` que aguardava desde 2026-07-31 19:41, mais 22 marcos de
prazo que a varredura enfileirou na hora (as sete tarefas vencidas do processo
`8c5ff6bf`, que nunca haviam sido varridas). Nenhuma falha: a fila terminou
inteira em `ENVIADA`, com 39 mensagens acumuladas no DEV.

O volume foi consequência do represamento, não do desenho: a chave de
deduplicação garante que cada marco dispare uma única vez por tarefa e
destinatário, então a varredura seguinte não repete nada.

### Aberto na Fase 9

- **backup não validado**: o `RUNBOOK.md` §6 define o que cobrir e como provar
  a restauração, inclusive a conferência de SHA-256 entre banco e storage, mas
  a execução com o DBA não aconteceu;
- a exportação monta o arquivo em memória e recusa acima de 5000 linhas. É
  suficiente para o volume do DEV; volume corporativo pedirá streaming, e aí a
  trilha precisará decidir o que registrar quando o download morre no meio;
- `MANIFEST.json` foi regenerado em 2026-08-01: os tamanhos anteriores eram do
  snapshot de 2026-07-30 e já não correspondiam aos documentos.

## Papéis funcionais atribuíveis (2026-08-03)

O catálogo funcional deixou de ter um único código. A fase é fatiada em cinco —
catálogo, atribuição exclusiva do SuperAdmin, override dos impedimentos, SPA e
documentação/homologação — e **a fatia 1 está implementada e comitada**.

Fatia 1 — catálogo, migration `accounts.0011`, **ainda não aplicada no Oracle
DEV**:

- `FUNCTIONAL_ROLE_CODES` passou a declarar cinco códigos: `DP`, `DP_GERENTE`,
  `GRUPOS_TEMPLATE_ADMIN`, `SETORES_ADMIN` e `USUARIOS_ADMIN`. A constraint
  `SGPD_CK_ROLE_ACTIVE_CODE` foi reescrita com os cinco; é alargamento puro, e
  toda linha existente já a satisfaz;
- `GLOBAL_ONLY_ROLE_CODES` fixa que os três papéis administrativos só existem em
  escopo global, e `AssignRoleService` recusa qualquer outro escopo para eles.
  Sem esse guard, a tela ofereceria um papel por empresa que `has_permission()`
  consultado sem empresa e sem filial nunca reconheceria;
- `ROLE_IMPLICATIONS` e `role_codes_satisfying()` (`apps/accounts/models.py`) são
  a fonte única da implicação `DP_GERENTE → DP`: onde uma regra exige o `DP`
  vigente no escopo, o gerente satisfaz. `has_effective_role()` a consulta, o
  que cobre os quatro pontos que passam por ela; os seis que filtram a atribuição
  por queryset — `_lock_people_department_assignments`, `processes_for_actor`,
  as duas barreiras de coordenador em `offboarding/api.py` e `reporting/api.py`,
  `_coordinates_processes` e `people_department_users` — passaram a usar
  `PEOPLE_DEPARTMENT_ROLE_CODES` com `__in`. Um deles esquecido daria ao gerente
  a autoridade do `DP` sem o hub, sem os relatórios e sem os avisos de prazo;
- `bootstrap_roles` reconcilia os cinco papéis com suas permissões:
  `GRUPOS_TEMPLATE_ADMIN` leva `manage_workflow_configuration`, `SETORES_ADMIN`
  leva `manage_sectors` e `USUARIOS_ADMIN` leva `manage_users`,
  `link_ad_identity` e `view_account_audit`. **Nenhum papel carrega
  `manage_roles`** — só o SuperAdmin atribui papel, e um teste fixa isso;
- `DP_GERENTE` repete as permissões do `DP` no catálogo, porque a implicação
  vale para papel exigido e não para permissão concedida: quem chama
  `has_permission()` não conhece a hierarquia.

A migration é `ALTER TABLE "SGPD_ROLE" DROP CONSTRAINT` seguido de `ADD
CONSTRAINT` com o mesmo nome, sobre tabela com uma linha; o nome tem 24
caracteres e não houve rewrite. Depois de aplicá-la, `bootstrap_roles` precisa
ser executado no DEV para criar os quatro papéis novos — até lá só existe o `DP`.

Validação padrão do backend por inteiro: 509 testes, Ruff, formatação, Mypy em
225 arquivos, Django check, verificação de migrations e `check --deploy` com os
dois avisos de HSTS que são opção deliberada. O frontend não foi tocado nesta
fatia, então Vitest e o build Angular não foram repetidos. Os cinco testes novos
cobrem o catálogo do `bootstrap_roles` alinhado a `FUNCTIONAL_ROLE_CODES` (sem
isso o bootstrap da conta técnica fica inalcançável em base nova), a ausência de
`manage_roles` em todo papel, a implicação que vale no escopo e não fora dele nem
no sentido inverso, o papel global recusado em escopo de empresa e aceito em
global, e a implicação chegando à visibilidade de processos, à barreira da API do
hub e aos destinatários de notificação.

## Endurecimento do host publicado (2026-08-03)

Uma checagem de segurança encontrou o host atendendo `sgpd.bsabioenergia.com.br`
com a configuração de desenvolvimento: `DJANGO_DEBUG=true` e cookies sem
`Secure`, enquanto o domínio já estava autorizado no `.env`. Qualquer erro
devolvia traceback com variáveis locais, e a sessão não exigia HTTPS.

O que mudou está normatizado na ADR-052. Em resumo:

- existe `config/settings/production.py`, que força `DEBUG` desligado, cookies
  `Secure`, redirecionamento para HTTPS com isenção da sonda de saúde, HSTS e
  reconhecimento do `X-Forwarded-Proto` do proxy. Ele **recusa subir** com
  `DJANGO_DEBUG` ligado ou `SECRET_KEY` curta;
- o módulo de settings passou a ser escolhido pelo `.env`, lido por
  `config/bootstrap.py` antes de o Django resolver o nome. Antes, a linha
  `DJANGO_SETTINGS_MODULE` do arquivo era inerte e o agendador subiria em
  desenvolvimento por mais correto que o `.env` estivesse;
- o limite de tentativas de login deixou de herdar `AnonRateThrottle`, que se
  desligava para quem já tinha sessão e agrupava todos os usuários numa chave
  só. Agora conta por origem e conta alvo, com `NUM_PROXIES` declarando a
  topologia — sem isso o `X-Forwarded-For` era forjável;
- o Django Admin ficou desligado no host publicado: seu login não passa pelo
  limite do DRF;
- o `DJANGO_SECRET_KEY` foi rotacionado, derrubando as sessões ativas. Custo
  zero de reconfiguração porque nenhum segredo da central estava gravado —
  a partir do primeiro, a rotação passa a exigir reinformá-los (R69);
- saíram do `.env` as variáveis que nenhum código lia e que guardavam senha em
  claro, entre elas uma que repetia a senha do bind do AD.

Verificado pela URL pública com a aplicação no ar: `health/ready` em 200, SPA
em 200, cookie CSRF com `Secure` e `SameSite=Lax`, HSTS presente, `/admin/` em
404, host não autorizado em 400, requisição HTTP sem o cabeçalho do proxy
redirecionada para HTTPS e a décima primeira tentativa de login recusada com
429. `check --deploy` termina apenas com os avisos de HSTS que são opção
deliberada.

Continua aberto e depende de infraestrutura: senhas fracas do Oracle e do SMTP
(R66), bind do AD com conta nominal sobre LDAP simples (R67) e `runserver`
atendendo o tráfego real (R68).

## Histórico

O registro integral até 2026-07-30 está em
`history/checkpoints/2026-07.md`. O plano concluído de migração da SPA está em
`history/completed-plans/MIGRATION_FRONTEND_SPA.md`.
