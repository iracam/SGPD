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
  host de produção, pelo Gunicorn sob systemd com um worker (ADR-055). **Desde
  2026-08-06 quem responde nessa URL é o host de produção da ADR-055**, com o
  serviço do host anterior parado — este último segue como DEV, apontando para o
  mesmo schema
- Concluído: os cinco papéis funcionais atribuíveis (ADR-054) — as cinco
  fatias implementadas, comitadas e **homologadas no Oracle DEV em
  2026-08-04**, com `accounts.0011` e
  `offboarding.0011_alter_offboardingprocess_options_and_more` aplicadas e o
  `bootstrap_roles` executado no ambiente
- Concluído: exclusão de processo não encerrado e cancelamento do já
  formalizado (ADR-056) — implementado, testado e validado localmente;
  `offboarding.0012` e `offboarding.0013` **aplicadas no Oracle em 2026-08-06**
- Concluído: preparação de produção (ADR-055) — Gunicorn sob systemd com um
  worker, `scripts/deploy.sh` com gate manual de migration, contrato de `.env` do
  host publicado e checklist de corte no `RUNBOOK.md` §11. **Corte executado em
  2026-08-06**: o host de produção responde pela URL publicada, com
  `/health/live/` e `/health/ready/` em 200 e usuários reais operando pela SPA
- Concluído: runtime assíncrono com Redis e Celery (ADR-057) — worker, Beat,
  cache compartilhado, despacho imediato por `on_commit` e batimento do
  agendamento na sonda. Os dois timers do systemd saíram. **Em produção desde
  2026-08-06**, com o `crontab` do DEV desativado. O despacho por `on_commit`
  ficou homologado ponta a ponta com e-mail real no próprio corte: as
  notificações saíram de um a dois segundos depois do fato, com `attempts=1`, e
  a fila está inteira em `ENVIADA` — 58 mensagens, nenhuma em `PENDENTE` ou
  `FALHA`, incluindo a que estava presa desde 2026-07-31
- **Acervo do banco zerado em 2026-08-06, a pedido**, por
  `scripts/reset_from_fixtures.sh` (`RUNBOOK.md` §6.1): ficou só a configuração
  — 30 contas, os 5 papéis com 15 atribuições, 12 setores com 31
  responsabilidades, 12 templates com 13 versões publicadas, 3 grupos de
  validação e os dois singletons da central. Saíram os 3 processos de teste, as
  pendências, as 58 notificações, as sessões e as três trilhas de auditoria. O
  despejo integral do instante anterior está em `docs/fixtures/`, fora do Git.
  As contagens de notificação e de fila citadas acima valem como registro do que
  foi homologado, não como estado atual
- Próximo incremento: fechar as validações do bloco **Depois** do
  `RUNBOOK.md` §11.3 que o corte deixou em aberto — nenhuma delas é observável
  do DEV, todas dependem do host de produção ou de uma sessão na tela:
  (a) batimento do agendamento em `/fe/operacao`, único sinal que prova o
  **Beat** de pé, já que a fila drenando prova apenas o worker;
  (b) `systemctl is-enabled sgpd-web sgpd-celery-worker sgpd-celery-beat`, para
  que os três sobrevivam a um reboot;
  (c) upload e download de uma evidência, que é o que exercita
  `/home/macari/prd/sgpd-data/evidence` pela primeira vez;
  (d) descoberta em `/fe/configuracoes/ldap`, prova de que o Fernet decifrou a
  senha de bind;
  (e) ensaio de supervisão com `systemctl kill -s SIGKILL sgpd-web`.
  Fora do repositório e aceitos com prazo: rotacionar as
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
de segurança. Com o **worker** fora, a fila acumula em `PENDENTE` e ninguém é
avisado. Com só o **Beat** fora é pior de enxergar: o despacho por `on_commit`
continua saindo do processo web, a fila fica em dia e apenas a varredura de
prazos deixa de acontecer. É o risco R63, e por isso `/fe/operacao` traz dois
sinais separados — a fila parada e o batimento vencido.

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

- o schema `SGPD` agora é **produtivo, com usuários reais dentro**, e o DEV
  continua apontando para ele. O `.env` do DEV traz
  `DJANGO_SETTINGS_MODULE=config.settings.production`, então qualquer
  `uv run manage.py <comando>` na árvore de desenvolvimento escreve na base viva.
  O mesmo vale para subir worker ou Beat no DEV pelo comando do `CLAUDE.md`: o
  broker é outro — Redis local, host distinto —, mas a fila e a varredura são as
  de produção. Até o schema do DEV se separar, leitura é o único uso seguro;
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
  cinco pretensões) **não existe mais** — a base foi refeita entre 2026-08-01 e
  2026-08-03. As seções históricas que citam aqueles UUIDs valem como registro
  do que foi exercido, não como estado atual. O acervo logo depois do corte de
  2026-08-06 era de 3 processos — dois `LIBERADO_PARA_RESCISAO` e um `INICIADO`
  —, 30 usuários e nenhuma evidência; o reset do mesmo dia zerou os processos;
- o usuário `homolog.visual` permanece desativado e com senha inutilizável. A FK
  da auditoria append-only impedia a exclusão; com as trilhas zeradas pelo reset
  de 2026-08-06 esse impedimento deixou de existir, e o que segura a conta agora
  é só a decisão de não mexer;
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
- o `crontab` do DEV instalado em 2026-08-01 foi desativado em 2026-08-06: as
  duas entradas continuam no arquivo, comentadas, e o worker e o Beat as cobrem.
  O resíduo do R63 mudou de forma — sem código de saída para o systemd marcar
  `failed`, quem testemunha o agendamento parado é a tela, e alguém precisa
  abri-la. A fila drenando não substitui esse olhar: o despacho por `on_commit`
  parte do processo web, então o Beat pode estar morto com a fila em dia e só a
  varredura de prazos deixando de acontecer;
- o storage privado de evidências **nunca foi exercido no host de produção**: a
  tabela `SGPD_EVIDENCE` está vazia, então o corte não teve bytes a copiar e
  `/home/macari/prd/sgpd-data/evidence` segue sem prova de permissão nem de
  `SGPD_EVIDENCE_ROOT`. O primeiro upload real é que vai dizer;
- um `FLUSHALL` ou reinício do Redis por aplicação vizinha zera o contador de
  tentativas de login em curso e descarta os sinais ainda não consumidos.
  Nenhuma notificação se perde — a fila é a tabela no Oracle;
- a URL base foi preenchida em 2026-08-06 com
  `https://sgpd.bsabioenergia.com.br` pela própria tela
  `/fe/configuracoes/email`, sem tocar no host; o link da notificação sai
  clicável. Como o valor mora no schema compartilhado, ele vale para DEV e PRD ao
  mesmo tempo;
- a fila chegou a 58 notificações, todas em `ENVIADA`: as 16 da homologação
  anterior, a da reabertura que ficou presa desde 2026-07-31 19:41 por falta de
  agendamento — drenada no corte — e as do uso real. A fila é append-only para a
  aplicação, que não tem caminho para apagá-la; o reset de 2026-08-06 a esvaziou
  por fora, pelo banco, junto com a auditoria e as pendências;
- as três exportações da homologação da Fase 9 deixaram três linhas em
  `SGPD_REPORT_EXPORT`, também append-only e também zeradas pelo reset;
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
