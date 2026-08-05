# Histórico documental

Esta árvore preserva documentos concluídos e registros de execução que não
fazem parte do contexto obrigatório cotidiano.

- `checkpoints/`: registros cronológicos imutáveis;
  - `2026-07.md` — checkpoint integral até 2026-07-30, da descoberta às Fases
    1 a 4;
  - `2026-08.md` — entregas e homologações de 2026-07-30 a 2026-08-04: Fases 6 a
    9, papéis funcionais (ADR-054), endurecimento do host (ADR-052) e manuais
    operacionais (ADR-053);
  - `2026-07-30-documentation-consolidation.md` — ata da consolidação documental
    que criou `CONTEXT.md` e `DECISIONS_INDEX.md`;
- `completed-plans/`: planos já executados.

Cada arquivo de checkpoint traz um índice de seções no topo. Para busca direta,
`grep -rn "<termo>" docs/SGPD/history/`.

Consulte este conteúdo somente para investigação, regressão, auditoria ou
rastreabilidade. O estado vigente está em `../CHECKPOINT.md`, que aponta para cá
na seção *Histórico*.
