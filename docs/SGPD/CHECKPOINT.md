# Checkpoint Atual do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Ambiente: DEV único sobre Oracle 19c
- Fases estabilizadas: 1, 2, 2.5 e 2.7
- Fases em andamento: 3 — configuração funcional; 4 — workflow
- Próximo incremento: Fase 5 — pendências e evidências
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
- abertura transacional em rascunho, snapshot e prevenção de duplicidade;
- seleção explícita de grupos e início idempotente;
- geração atômica de tarefas e snapshots de checklist;
- início, respostas simples e conclusão de tarefa com versão otimista, lock,
  idempotência e auditoria;
- hub de processos e cards agrupados de tarefas ativas/concluídas.

## Estado corrente

O cadastro funcional básico está operacional. Regras automáticas de
aplicabilidade permanecem pendentes. O fluxo de processo cobre abertura,
seleção, início e ciclo inicial das tarefas. Itens que exigem arquivo ou
evidência aguardam a Fase 5.

O card de concluídos pode derivar conclusão operacional quando todas as tarefas
estão concluídas. A transição formal `ENCERRADO`, prontidão e liberação ainda
não foram implementadas.

## Incremento autorizado

Fase 5 — pendências e evidências:

- pendência e seus itens como entidades próprias;
- comentários e estados de regularização;
- evidências privadas, metadados e hash;
- autorização por processo, setor, DP e SuperAdmin;
- bloqueio de conclusão/liberação conforme regras;
- services transacionais, concorrência, idempotência e auditoria;
- API e SPA sem regra de negócio no cliente;
- testes de caminho feliz, negação, estado inválido, rollback, auditoria,
  concorrência e dados incompletos.

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
- homologar regras automáticas de aplicabilidade;
- definir retenção operacional das evidências;
- paginação visual adicional dos painéis pode ser necessária com maior volume;
- o estado formal de encerramento e sua data aguardam a Fase 8.

## Baseline de qualidade

No último incremento concluído passaram 328 testes backend e 73 frontend,
Ruff, formatação, Mypy, Django check, verificação de migrations e build Angular.
Cada nova mudança deve executar o subconjunto pertinente e justificar qualquer
validação omitida.

## Histórico

O registro integral até 2026-07-30 está em
`history/checkpoints/2026-07.md`. O plano concluído de migração da SPA está em
`history/completed-plans/MIGRATION_FRONTEND_SPA.md`.
