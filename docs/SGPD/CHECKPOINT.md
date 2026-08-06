# Checkpoint Atual do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Ambiente: DEV e host de produção (ADR-055), ambos sobre o mesmo schema `SGPD`
  no Oracle 19c
- Fases estabilizadas: 1, 2, 2.5, 2.7, 3, 6, 7, 8 e **9 — implementada e
  homologada no Oracle DEV em 2026-08-01**
- Fases em andamento: 4 — workflow; 5 — pendências e evidências
- Publicação: `https://sgpd.bsabioenergia.com.br` por proxy em outro host desde
  2026-08-03; a aplicação sobe com `config.settings.production` (ADR-052) e, no
  host de produção, pelo Gunicorn sob systemd com um worker (ADR-055)
- Concluído: os cinco papéis funcionais atribuíveis (ADR-054) — as cinco
  fatias implementadas, comitadas e **homologadas no Oracle DEV em
  2026-08-04**, com `accounts.0011` e
  `offboarding.0011_alter_offboardingprocess_options_and_more` aplicadas e o
  `bootstrap_roles` executado no ambiente
- Concluído: exclusão de processo não encerrado e cancelamento do já
  formalizado (ADR-056) — implementado, testado e validado localmente;
  `offboarding.0012` e `offboarding.0013` **ainda não aplicadas no Oracle**
- Concluído: preparação de produção (ADR-055) — Gunicorn sob systemd com um
  worker, `scripts/deploy.sh` com gate manual de migration, contrato de `.env` do
  host publicado e checklist de corte no `RUNBOOK.md` §11. **Implementado e
  validado localmente; ainda não executado no host de produção**
- Concluído: runtime assíncrono com Redis e Celery (ADR-057) — worker, Beat,
  cache compartilhado, despacho imediato por `on_commit` e batimento do
  agendamento na sonda. Os dois timers do systemd saíram. **Implementado,
  testado e validado localmente contra o Redis do host; as units ainda não
  foram instaladas no PRD e o `crontab` do DEV ainda precisa ser removido**
- Próximo incremento: executar o corte pelo checklist do `RUNBOOK.md` §11 —
  provisionar o host, levar o mesmo `DJANGO_SECRET_KEY` (ou reinformar as senhas
  da central), copiar as evidências para `/home/macari/prd/sgpd-data/evidence`,
  parar o serviço anterior e
  reapontar o proxy. Fora do repositório e aceitos com prazo: rotacionar as
  senhas do Oracle e do SMTP (R66), trocar o bind do AD por conta de serviço com
  TLS (R67), validar backup e restauração com o DBA (`RUNBOOK.md` §6) e criar o
  usuário Oracle de aplicação separado do owner
- Configuração técnica: LDAP e e-mail administrados na central por SuperAdmin;
  o `.env` é baseline do primeiro boot (ADR-031, ADR-050)
- Runtime assíncrono: Redis do host, compartilhado com outras aplicações, como
  broker e cache; worker e Beat do Celery no lugar do agendador do sistema
  operacional (ADR-057)
- Interface: SPA Angular 21; Django Admin técnico preservado
- Autorização: SuperAdmin global; cinco papéis atribuíveis (ADR-054), com
  `DP_GERENTE` satisfazendo `DP` e podendo passar por cima de impedimento sob
  justificativa; responsabilidade de setor derivada do vínculo vigente;
  segregação de valores pela ADR-048

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
- exclusão definitiva do processo não encerrado, com aviso quantificado antes de
  confirmar, justificativa obrigatória e lápide append-only em
  `SGPD_PROCESS_PURGE` guardando a trilha copiada (ADR-056);
- notificações por e-mail com outbox no Oracle, varredura de prazos, escaladas,
  painel de falhas e reprocessamento auditado;
- central de configuração de e-mail: transporte SMTP, remetente, URL base, ritmo
  da fila e marcos de lembrete editáveis por SuperAdmin, com prova de envio;
- indicadores do painel, relatórios por período, exportação CSV auditada e sonda
  de operação, todos somente leitura em `apps/reporting`;
- manuais operacionais em `docs/operacao/`, um por público do catálogo de papéis
  (ADR-054) — primeiros passos, responsável de área, Departamento Pessoal,
  configuração, administração de usuários e SuperAdmin —, gerados de `.md` para
  HTML e PDF por `docs/operacao/build.mjs` e servidos em `/ajuda/<slug>/` atrás
  da sessão (ADR-053), com botão **Ajuda** em Painel, Minha senha, Minhas
  tarefas, Processos, Setores, Grupos e templates, Usuários, ficha do usuário,
  Auditoria, Configurações, LDAP, E-mail e Operação — 13 telas, com teste que
  casa cada âncora com o `id` do HTML gerado; só Relatórios segue sem botão.

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
valor gravam a mensagem na mesma transação do fato. Quem despacha é o worker do
Celery e quem dispara a agenda periódica é o Beat (ADR-057); o aviso de um ato
feito na tela sai em segundos, por `on_commit`, e a varredura periódica é a rede
de segurança. Com o worker ou o Beat fora, a fila acumula em `PENDENTE` e
ninguém é avisado — é o risco R63, agora visível por dois sinais em
`/fe/operacao`: a fila parada e o batimento vencido.

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
- migrations exigem inspeção do SQL Oracle antes de aplicação; o
  `scripts/deploy.sh` para diante de migration pendente em vez de aplicá-la;
- o host publicado roda com **um worker por escolha operacional**: a trava caiu
  com o cache compartilhado no Redis (ADR-057), e `config.settings.production` só
  recusa `WEB_CONCURRENCY` acima de 1 se alguém devolver o cache ao processo.
  Subir a concorrência exige medir Oracle e pool de conexões antes;
- o Redis é do host e compartilhado com outras aplicações: o projeto o consome,
  não o gerencia, e convive por índice dedicado, `KEY_PREFIX` e fila nomeada;
- enquanto DEV e PRD apontarem para o mesmo schema, o `DJANGO_SECRET_KEY` é o
  mesmo nos dois: dele deriva a cifra dos segredos da central (R69);
- exclusão de processo é a única operação que destrói dado: `ENCERRADO` nunca é
  alcançado, a justificativa é obrigatória e não existe desfazer. Como DEV e PRD
  dividem o schema (ADR-055), excluir em um exclui no outro;
- não antecipar desconto automático; liberação e encerramento existem apenas
  como ato humano explícito, nunca como consequência automática de estado;
- e-mail de notificação não carrega nome do colaborador, CPF, valor nem
  parecer: o corpo diz o que fazer e onde, e o dado fica no sistema
  (`SECURITY.md` §13.1);
- valor é pretensão sujeita a análise (ADR-009): o SGPD nunca aplica desconto,
  e `VALOR_PROCESSADO` só é preenchido a partir do registro do Senior.

## Riscos e pendências relevantes

- `offboarding.0012` (constraint `SGPD_CK_PROCESS_FORMAL` reescrita para o
  cancelado preservar marcas) e `offboarding.0013` (tabela `SGPD_PROCESS_PURGE` e
  texto da permissão) foram revisadas no SQL Oracle e **ainda não aplicadas**: a
  0012 é drop/add de check constraint, validada contra as linhas existentes, e a
  0013 só cria tabela nova. Nenhuma toca dado;
- a exclusão remove o processo dos indicadores e relatórios retroativamente,
  porque `apps/reporting` calcula tudo na leitura. O número congelado só existe
  nas exportações CSV já registradas em `SGPD_REPORT_EXPORT`;
- se o `unlink` do arquivo de evidência falhar depois do commit da purga, sobra
  arquivo órfão no storage privado; a lápide lista os caminhos e o log registra
  a falha com o `correlation_id`;
- homologar o limite de 10 MiB e o catálogo inicial PDF/PNG/JPEG;
- o expurgo de evidências é manual: a retenção de 5 anos está definida e o
  encerramento formal já dá o marco de contagem, mas não há rotina automática;
- validar a retenção de 5 anos com Jurídico, RH e Segurança da Informação;
- paginação visual adicional dos painéis pode ser necessária com maior volume;
- o conjunto de dados de homologação das fases anteriores (`5bfc0d3a`,
  `8c5ff6bf`, `9cbed216`, `c8787348` e `d80327c7`, com as seis pendências e as
  cinco pretensões) **não existe mais no DEV** — a base foi refeita entre
  2026-08-01 e 2026-08-03. Restou um único processo, `222e587b`. As seções
  históricas que citam aqueles UUIDs valem como registro do que foi exercido,
  não como estado atual;
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
- o `crontab` do DEV instalado em 2026-08-01 **precisa ser removido**: o worker e
  o Beat cobrem as duas entradas, e deixar as duas coisas rodando dobraria o
  trabalho à toa. O resíduo do R63 mudou de forma — sem código de saída para o
  systemd marcar `failed`, quem testemunha o agendamento parado é a tela, e
  alguém precisa abri-la;
- um `FLUSHALL` ou reinício do Redis por aplicação vizinha zera o contador de
  tentativas de login em curso e descarta os sinais ainda não consumidos.
  Nenhuma notificação se perde — a fila é a tabela no Oracle;
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

## Baseline de qualidade

A validação padrão vigente, executada por inteiro na última entrega
(2026-08-06): **554 testes backend e 139 frontend**, Ruff, formatação, Mypy em
234 arquivos, Django check, verificação de migrations, `check --deploy` com os
dois avisos de HSTS já deliberados e build Angular sem avisos. Desde a ADR-057 o
boot real confirma o inverso do que confirmava antes: `WEB_CONCURRENCY=4 uv run
manage.py check --deploy` **sobe**, porque o cache é compartilhado — e a suíte
guarda a trava para o caso de alguém devolver o cache ao processo. Toda mudança
executa o subconjunto pertinente e justifica qualquer validação omitida.

Duas armadilhas do Oracle que a suíte já cobre e que nenhuma mudança deve
reintroduzir estão descritas em *Riscos e pendências relevantes*: constraint de
campo anulável precisa admitir o nulo na condição, e `CharField` anulável
volta como `''`, nunca `None`. O replay idempotente materializa
`select_for_update()` sem paginação, porque o Oracle não combina `FOR UPDATE`
com `FETCH FIRST`.

O número de testes por incremento, o defeito que cada regressão fixou e o SQL
revisado de cada migration estão no histórico — ver abaixo.

## Histórico

Este documento guarda **apenas o estado vigente**. O registro cronológico de
entregas, homologações, defeitos corrigidos e validações por incremento foi
arquivado em `history/`, que não é leitura obrigatória: consulte-o para
investigação, regressão, auditoria ou rastreabilidade.

| Onde procurar | O que tem | Período |
| --- | --- | --- |
| `history/checkpoints/2026-07.md` | Checkpoint integral da descoberta às Fases 1–4: ambiente, decisões de fundação e registro de entrega por incremento. | até 2026-07-30 |
| `history/checkpoints/2026-08.md` | Fases 6 a 9, papéis funcionais (ADR-054), endurecimento do host (ADR-052) e manuais operacionais (ADR-053), com as homologações no Oracle DEV e a baseline de qualidade de cada incremento. Índice de seções no topo do arquivo. | 2026-07-30 a 2026-08-04 |
| `history/checkpoints/2026-07-30-documentation-consolidation.md` | Ata da consolidação documental que criou `CONTEXT.md` e `DECISIONS_INDEX.md`. | 2026-07-30 |
| `history/completed-plans/MIGRATION_FRONTEND_SPA.md` | Plano concluído da migração para a SPA Angular. | — |

Para achar um fato específico: **por que** uma decisão foi tomada está em
`DECISIONS.md` (localize pelo `DECISIONS_INDEX.md`); **o que** o sistema faz
hoje está aqui e no documento especializado correspondente pela matriz do
`CONTEXT.md`; **quando e como** algo foi exercido ou corrigido está no
histórico acima — comece pelo índice de seções de cada arquivo e, se não
bastar, `grep -rn "<termo>" docs/SGPD/history/`.
