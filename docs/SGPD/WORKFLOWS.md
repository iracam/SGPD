# Fluxos e Estados

## 1. Fluxo principal

```text
DP abre processo
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
DP confirma ou ajusta os setores
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
          Análise final do DP
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

Permitido:

- alterar dados;
- incluir ou remover grupos;
- revisar colaborador;
- cancelar.

### INICIADO

Processo formalmente iniciado e tarefas geradas.

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

DP autorizou o prosseguimento.

### RESCISAO_PROCESSADA

Rescisão registrada como processada no Senior.

### ENCERRADO

Processo concluído e bloqueado para alterações comuns.

### CANCELADO

Processo cancelado com justificativa.

## 3. Estados da tarefa de setor

- PENDENTE
- EM_ANALISE
- SEM_PENDENCIA
- COM_PENDENCIA
- AGUARDANDO_REGULARIZACAO
- REGULARIZADA
- APROVADA_COM_RESSALVA
- CONCLUIDA
- CANCELADA

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
- responsáveis resolvidos ou fila de responsabilidade configurada.

### Em validação para pronto para análise do DP

Pré-condições:

- todas as tarefas obrigatórias concluídas;
- itens obrigatórios respondidos;
- evidências obrigatórias anexadas;
- pendências bloqueantes sem estado indefinido.

### Pronto para análise do DP para liberado

Pré-condições:

- DP revisou o consolidado;
- valores foram analisados;
- exceções possuem decisão;
- usuário possui permissão de liberação.

### Liberado para encerrado

Pré-condições:

- rescisão processada ou confirmação manual autorizada;
- número ou evidência de processamento registrada;
- pendências finais encerradas.

## 6. Prazos

Cada tarefa poderá herdar prazo de:

1. regra específica;
2. template;
3. setor;
4. parâmetro global.

Cálculo sugerido:

```text
prazo_tarefa = menor(data_limite_processo, data_abertura + SLA_setor)
```

O sistema deverá considerar calendário útil configurável em fase posterior.

## 7. Escalada

Exemplo:

- 48 horas antes: lembrete ao responsável;
- 24 horas antes: lembrete ao responsável e coordenador;
- vencido: coordenador e DP;
- vencido crítico: gestor da área e DP;
- processo próximo ao limite: alerta consolidado.

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
