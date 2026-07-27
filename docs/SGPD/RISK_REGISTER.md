# Registro Inicial de Riscos

| ID | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---:|---:|---|
| R01 | Acoplamento às tabelas internas do Senior | Alta | Alto | Usar views e contrato homologado |
| R02 | Uso do owner pela aplicação | Média | Alto | Separar SGPD_OWNER, SGPD_APP e SGPD_SYNC |
| R03 | Dados de colaborador alterados após abertura | Alta | Alto | Snapshot imutável |
| R04 | Checklist alterado afetar histórico | Alta | Alto | Versionamento |
| R05 | Desconto indevido | Média | Muito alto | Pretensão, aprovação e segregação |
| R06 | Acesso indevido a documentos médicos | Média | Muito alto | Autorização por classe e setor |
| R07 | E-mails não enviados | Média | Médio | Fila, retry e painel de falhas |
| R08 | Responsável ausente | Alta | Médio | Substituto, fila e escalada |
| R09 | Processo travado por regra mal configurada | Média | Alto | Simulação e validação de regras |
| R10 | Duplicidade de processo | Média | Alto | Regra de unicidade e validação |
| R11 | Sincronização inconsistente | Média | Alto | Idempotência e reconciliação |
| R12 | Migration com lock no Oracle | Média | Alto | Revisão de SQL e janela de mudança |
| R13 | Auditoria incompleta | Média | Alto | Service de auditoria e testes |
| R14 | Upload malicioso | Média | Alto | Validação, antivírus e storage privado |
| R15 | Escopo crescer antes do MVP | Alta | Alto | Roadmap e checkpoints |
