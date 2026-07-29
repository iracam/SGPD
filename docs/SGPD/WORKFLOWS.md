# Fluxos e Estados

## Estado do documento

Este documento define o fluxo funcional alvo. A abertura em `RASCUNHO`, a
seleção versionada e a transição idempotente para `INICIADO` estão
implementadas. O ciclo inicial da tarefa `PENDENTE → EM_ANALISE → CONCLUIDA`
e as respostas simples de checklist também estão implementados; as demais
transições deverão ser confirmadas e testadas nos checkpoints das Fases 4 a 8.

## 1. Fluxo principal

```text
Usuário com papel DP vigente abre o processo
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
Usuário com papel DP confirma ou ajusta os setores
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
     Análise final por usuário com papel DP
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

Processo concluído e bloqueado para alterações comuns.

### CANCELADO

Processo cancelado com justificativa.

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
exige a tarefa em análise e todas as respostas obrigatórias válidas. Ambas as
ações usam locks, versão otimista, chave idempotente e auditoria na mesma
transação. Respostas que dependem de arquivo/evidência aguardam a Fase 5 e não
podem concluir a tarefa. Neste incremento a conclusão da última tarefa não
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

Exemplo:

- 48 horas antes: lembrete ao responsável;
- 24 horas antes: lembrete a todos os responsáveis do setor;
- vencido: alerta a todos os responsáveis e aos responsáveis do Departamento
  Pessoal;
- vencido crítico: reforço aos mesmos destinatários;
- processo próximo ao limite: alerta consolidado.

Quando houver mais de um responsável, todos recebem os avisos e podem agir. A
primeira transação válida movimenta a tarefa; tentativas posteriores observam
o novo estado e não repetem efeitos.

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
