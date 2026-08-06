# Fluxos e Estados

## Estado do documento

Este documento define o fluxo funcional alvo. A abertura em `RASCUNHO`, a
seleção versionada e a transição idempotente para `INICIADO` estão
implementadas. O ciclo da tarefa `PENDENTE → EM_ANALISE → CONCLUIDA`, as
respostas do checklist e a primeira fatia de pendências/evidências estão
implementados; as demais transições deverão ser confirmadas e testadas nos
checkpoints das Fases 6 a 8.

## Premissa de autoridade global

SuperAdmin ativo e autenticado pode consultar e executar qualquer processo,
tarefa e transição exposta pelo SGPD, sem atribuição `DP` ou vínculo de setor.
Essa premissa substitui apenas a checagem de autorização: estados, bloqueios,
prontidão, segregação, concorrência, idempotência e auditoria permanecem
obrigatórios.

## 1. Fluxo principal

```text
Usuário com papel DP vigente ou SuperAdmin abre o processo
    |
    v
Sistema consulta o Senior em tempo real por SELECT parametrizado
    |
    v
Sistema cria snapshot do colaborador
    |
    v
Sistema sugere grupos de validação
    |
    v
Usuário com papel DP ou SuperAdmin confirma ou ajusta os setores
    |
    v
Sistema gera tarefas e checklists
    |
    +-------------------------------+
    |                               |
    v                               v
Setor A valida                  Setor B valida
    |                               |
    v                               v
Pendências / evidências         Pendências / evidências
    |                               |
    +---------------+---------------+
                    |
                    v
        Consolidação automática
                    |
                    v
     Análise final por DP ou SuperAdmin
                    |
          +---------+---------+
          |                   |
          v                   v
      Correção            Liberação
                              |
                              v
                   Rescisão no Senior HCM
                              |
                              v
                         Encerramento
```

## 2. Estados do processo

### RASCUNHO

Processo criado, mas ainda não iniciado.

Implementado: usuário com `DP` vigente seleciona o colaborador, o service relê
o Senior, revalida a autoridade dentro da transação e grava processo, snapshot
e `PROCESS_OPENED`. Depois, o DP fixa versões publicadas de grupos e pode usar
ajustes manuais justificados pela API.

Permitido:

- alterar dados;
- incluir ou remover grupos;
- revisar colaborador;
- cancelar.

### INICIADO

Processo formalmente iniciado e tarefas geradas.

Implementado: o início revalida autoridade e configuração sem reler o Senior,
trava o agregado e cria tarefas/perguntas históricas, auditoria e idempotência
na mesma transação.

### EM_VALIDACAO

Existe ao menos uma tarefa em andamento.

### COM_PENDENCIAS

Existe pendência aberta.

### AGUARDANDO_REGULARIZACAO

Uma ou mais pendências aguardam solução.

### AGUARDANDO_DECISAO

Existe valor, contestação ou caso que depende de aprovação.

### PRONTO_PARA_ANALISE_DP

Todos os setores concluíram suas tarefas.

### LIBERADO_PARA_RESCISAO

Usuário com papel `DP` vigente no escopo autorizou o prosseguimento.

### RESCISAO_PROCESSADA

Rescisão registrada como processada no Senior.

### ENCERRADO

Processo concluído e bloqueado para alterações comuns. É o único estado que a
exclusão nunca alcança (ADR-056): para desfazê-lo, cancele.

### CANCELADO

Processo cancelado com justificativa. Alcança rascunho e iniciado pelo `DP`
vigente no escopo e, pela ADR-056, também o liberado, o processado e o
encerrado — nesses três, sob `offboarding.override_process_blockers`, isto é,
`DP_GERENTE` ou SuperAdmin.

O cancelado **preserva as marcas formais que já existiam**: liberação,
processamento e encerramento continuam gravados com data e ator. Cancelar
acrescenta o desfecho, não apaga o percurso. Continua sendo terminal — não há
reabertura de cancelado.

### Exclusão (fora da máquina de estados)

Excluir não é transição: o processo deixa de existir. Alcança todos os estados
**menos `ENCERRADO`**, exige justificativa e deixa a lápide append-only em
`SGPD_PROCESS_PURGE`, com a trilha copiada. O `DP` exclui o que não produziu
nada; com tarefa concluída, pendência ou evidência, é ato da gerência. Ver
RF-038 e ADR-056.

## 3. Estados da tarefa de setor

- PENDENTE — implementado;
- EM_ANALISE — implementado;
- SEM_PENDENCIA
- COM_PENDENCIA
- AGUARDANDO_REGULARIZACAO
- REGULARIZADA
- APROVADA_COM_RESSALVA
- CONCLUIDA — implementado;
- CANCELADA

O responsável vigente no escopo inicia a análise explicitamente. A conclusão
exige a tarefa em análise, todas as respostas obrigatórias válidas, evidências
obrigatórias presentes e nenhuma pendência bloqueante aberta ou em
regularização. As ações usam locks, versão otimista, chave idempotente e
auditoria na mesma transação. Arquivos são enviados antes da conclusão pelo
endpoint privado da Fase 5. Neste incremento a conclusão da última tarefa não
altera automaticamente o estado do processo.

## 4. Estados da pendência

- ABERTA
- COMUNICADA
- RECONHECIDA
- CONTESTADA
- EM_REGULARIZACAO
- REGULARIZADA
- ENCAMINHADA_ANALISE
- APROVADA_COBRANCA
- REJEITADA
- ABONADA
- ENCERRADA

Implementado no eixo de regularização:

- `ABERTA → EM_REGULARIZACAO`;
- `EM_REGULARIZACAO → REGULARIZADA`;
- `REGULARIZADA → ENCERRADA`;
- `REGULARIZADA → EM_REGULARIZACAO`, quando a regularização precisar ser
  retomada.

Implementado no eixo de decisão, na Fase 6:

- `ABERTA → ENCAMINHADA_ANALISE`, ao lançar a pretensão de cobrança;
- `ENCAMINHADA_ANALISE → CONTESTADA` e `CONTESTADA → ENCAMINHADA_ANALISE`,
  quando a contestação é registrada e a apuração é refeita;
- `ENCAMINHADA_ANALISE` ou `CONTESTADA → APROVADA_COBRANCA`, `REJEITADA` ou
  `ABONADA`, conforme a decisão;
- `APROVADA_COBRANCA`, `REJEITADA` ou `ABONADA → ENCERRADA`.

O eixo de decisão só é alcançado pelos services de valor, que exigem pretensão
registrada em pendência de categoria `VALOR` e setor com `PERMITE_VALOR`. O
endpoint genérico de situação não entra nele; dele só tem saída para o
encerramento. `COMUNICADA` e `RECONHECIDA` permanecem na Fase 7, junto com a
notificação que lhes dá sentido.

As demais situações acima permanecem como fluxo alvo de comunicação e decisão
dos incrementos posteriores. Toda transição implementada exige comentário e
preserva concorrência, idempotência e auditoria.

## 5. Regras de transição

### Rascunho para iniciado

Pré-condições:

- colaborador válido;
- snapshot criado;
- data limite informada;
- pelo menos um setor obrigatório;
- cada setor selecionado ativo e compatível com o escopo do processo;
- ao menos um vínculo de responsável efetivo para cada setor obrigatório no
  instante do início.

Grupos sobrepostos para o mesmo setor são consolidados somente quando fixam o
mesmo template: obrigatoriedade e bloqueio usam `OR`, e prevalece o menor SLA.
Templates diferentes para o mesmo setor bloqueiam o início.

O início não escolhe um responsável individual. A tarefa pertence ao setor e
todos os seus responsáveis efetivos, de igual autoridade, podem agir conforme
o escopo vigente.

### Em validação para pronto para análise do DP

Pré-condições:

- todas as tarefas obrigatórias concluídas;
- itens obrigatórios respondidos;
- evidências obrigatórias anexadas;
- pendências bloqueantes sem estado indefinido.

### Pronto para análise do DP para liberado

Pré-condições:

- usuário com papel `DP` vigente no escopo revisou o consolidado;
- valores foram analisados;
- exceções possuem decisão;
- usuário possui permissão de liberação.

### Liberado para encerrado

Pré-condições:

- rescisão processada ou confirmação manual autorizada;
- número ou evidência de processamento registrada;
- pendências finais encerradas.

## 6. Prazos

Cada tarefa herda prazo de:

1. ajuste manual do rascunho;
2. sobrescrita do grupo;
3. template;
4. setor.

Cálculo implementado neste incremento:

```text
prazo_tarefa = menor(fim_da_data_limite_processo, data_inicio + SLA_resolvido)
```

O sistema ainda não considera calendário útil; essa evolução exige nova
homologação e não deve recalcular tarefas já criadas.

### Idempotência do início

A chave é única por processo e ação `START`. Repetir a mesma chave, corpo e
ator devolve a transição anterior sem novo efeito. Reutilizar a chave com corpo
ou ator diferente retorna conflito. Qualquer falha remove tarefas, auditoria e
registro idempotente pelo rollback da mesma transação.

### Idempotência das tarefas

Início e conclusão usam uma chave por tarefa e ação. Repetir a mesma chave,
ator, versão esperada e corpo devolve replay sem nova auditoria. Reusar a chave
com conteúdo ou ator diferente retorna conflito. Falha de resposta, auditoria
ou persistência reverte tarefa, checklist e idempotência em conjunto.

## 7. Escalada

Implementada na Fase 7. A varredura lê prazos e enfileira avisos; ela não
movimenta nada no domínio.

| Marco | Quando dispara | Quem recebe |
| --- | --- | --- |
| `TAREFA_A_VENCER` | 48 h antes do prazo da tarefa | responsáveis vigentes do setor |
| `TAREFA_VENCE_EM_BREVE` | 24 h antes do prazo | responsáveis vigentes do setor |
| `TAREFA_VENCIDA` | no vencimento | responsáveis do setor e `DP` do escopo |
| `TAREFA_VENCIDA_CRITICA` | 48 h após o vencimento | os anteriores e os responsáveis do setor de escalada |
| `PROCESSO_PROXIMO_LIMITE` | 72 h antes da data limite, com tarefa em aberto | `DP` do escopo |

As janelas são configuráveis por variável de ambiente
(`NOTIFICATION_TASK_*_HOURS`, `NOTIFICATION_PROCESS_DUE_SOON_HOURS`) e os
valores acima são o padrão.

Não há dono individual de tarefa: como a responsabilidade é do setor e todos os
responsáveis vigentes têm a mesma autoridade (ADR-038), o lembrete de 48 h
também vai ao conjunto inteiro. A primeira transação válida movimenta a tarefa;
tentativas posteriores observam o novo estado e não repetem efeitos.

Cada marco dispara uma única vez por tarefa e destinatário: a chave de
deduplicação é única no banco, então repetir a varredura muda a latência do
aviso, nunca a quantidade. `DP` ausente no escopo ou setor sem responsável
vigente fazem o marco ser contado como “sem destinatário” e registrado em log —
o aviso não sai e ninguém é avisado disso automaticamente.

## 8. Reabertura

Reabertura exige:

- permissão especial;
- justificativa;
- identificação do motivo;
- registro do estado anterior;
- notificação aos setores afetados.

## 9. Cancelamento

Cancelamento exige:

- motivo;
- usuário;
- data e hora;
- observação;
- cancelamento das tarefas abertas;
- preservação integral da auditoria.
