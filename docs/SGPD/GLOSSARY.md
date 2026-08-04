# Glossário

## DP

Papel funcional do Departamento Pessoal que coordena o ciclo demissional:
abertura, acompanhamento, análise, liberação e encerramento. Pode coexistir
com a capacidade derivada `RESPONSAVEL_SETOR` e não é concedido
automaticamente pela associação ao setor Departamento Pessoal.

## DP_GERENTE

Papel funcional da gerência do Departamento Pessoal. Satisfaz toda exigência de
`DP` sem atribuição própria e é o único do catálogo que pode liberar e encerrar
processo com impedimentos, mediante justificativa registrada (ADR-054).

## Papéis administrativos

`GRUPOS_TEMPLATE_ADMIN`, `SETORES_ADMIN` e `USUARIOS_ADMIN` — configuração de
workflow, setores e contas, respectivamente. Existem somente em escopo global e
não coordenam processo.

## Override de impedimento

Ato explícito de liberar ou encerrar um processo que a prontidão recusaria,
autorizado por `offboarding.override_process_blockers`, sempre com
justificativa e trilha. Dispensa a prontidão e nada mais.

## RESPONSAVEL_SETOR

Capacidade funcional derivada de vínculo vigente entre usuário e setor. Não é
papel atribuível e herda o escopo organizacional do próprio setor.

## Processo demissional

Conjunto de atividades necessárias para validar e liberar o desligamento.

## Senior HCM

Sistema oficial de gestão de pessoas e processamento da rescisão.

## Setor de validação

Área responsável por analisar algum aspecto do desligamento.

## Grupo de validação

Conjunto reutilizável de setores aplicáveis a determinado perfil de colaborador.

## Template de checklist

Modelo versionado de perguntas de um setor.

## Tarefa

Instância de validação de um setor dentro de um processo.

## Pendência

Registro estruturado de algo que precisa ser resolvido, decidido ou documentado.

## Evidência

Arquivo ou documento que sustenta uma resposta, pendência ou decisão.

## Pretensão de cobrança

Valor informado por uma área para análise, sem representar desconto automático.

## Snapshot

Cópia imutável dos dados do colaborador no momento da abertura.

## Bloqueante

Condição que impede a liberação do processo.

## Prontidão

Resultado da avaliação automática das condições de liberação.

## Liberação

Ação explícita de usuário com o papel `DP` vigente no escopo autorizando o
prosseguimento da rescisão.

## Encerramento

Conclusão do processo após a rescisão ser registrada como processada.
