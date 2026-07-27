# Registro Inicial de Riscos

| ID | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---:|---:|---|
| R01 | Acoplamento às tabelas internas do Senior | Alta | Alto | Contrato SQL homologado, objetos qualificados, testes de contrato e revisão a cada upgrade |
| R02 | Uso do owner `SGPD` pela aplicação ampliar impacto de falha ou credencial comprometida | Decisão aceita no DEV | Muito alto | `.env` 600, SQL centralizado, sem DDL no runtime, migrations revisadas, auditoria e reavaliação antes de outro ambiente |
| R03 | Dados de colaborador alterados após abertura | Alta | Alto | Snapshot imutável |
| R04 | Checklist alterado afetar histórico | Alta | Alto | Versionamento |
| R05 | Desconto indevido | Média | Muito alto | Pretensão, aprovação e segregação |
| R06 | Acesso indevido a documentos médicos | Média | Muito alto | Autorização por classe e setor |
| R07 | E-mails não enviados | Média | Médio | Fila, retry e painel de falhas |
| R08 | Responsável ausente | Alta | Médio | Substituto, fila e escalada |
| R09 | Processo travado por regra mal configurada | Média | Alto | Simulação e validação de regras |
| R10 | Duplicidade de processo | Média | Alto | Regra de unicidade e validação |
| R11 | Indisponibilidade ou lentidão do Senior bloquear novas pesquisas | Média | Alto | Timeout, paginação, filtros, health check e erro explícito sem usar dados obsoletos |
| R12 | Migration com lock no Oracle | Média | Alto | Revisão de SQL e janela de mudança |
| R13 | Auditoria incompleta | Média | Alto | Service de auditoria e testes |
| R14 | Upload malicioso | Média | Alto | Validação, antivírus e storage privado |
| R15 | Escopo crescer antes do MVP | Alta | Alto | Roadmap e checkpoints |
| R16 | Divergência futura da versão Python homologada | Baixa | Médio | Python 3.13 fixado no `pyproject.toml`, ambiente isolado e `uv.lock` versionado |
| R17 | Filesystem local com 96% de utilização | Alta | Alto | Liberar ou ampliar espaço antes de imagens, dependências e evidências |
| R18 | Criação futura de HML ou PRD sem paridade com DEV | Baixa | Alto | Exigir nova decisão e inventário antes de ampliar ambientes |
| R19 | Exposição do `.env` local com credenciais | Média | Muito alto | Ignorar no Git, restringir permissões e nunca registrar valores em logs |
| R20 | Ferramentas Python globais com versões divergentes | Alta | Médio | Usar ambiente virtual e lockfile do projeto |
| R21 | Vinculação futura ao AD associar a identidade errada ou duplicada | Média | Muito alto | Identificador corporativo estável e único, confirmação administrativa, auditoria e teste de duplicidade |
| R22 | Uso indevido do WhiteNoise para evidências ou uploads | Média | Muito alto | Restringir WhiteNoise a estáticos e usar storage privado para evidências |
| R23 | Ausência de CI/CD permitir validações locais inconsistentes | Média | Médio | Padronizar comandos locais e registrar evidências de testes |
| R24 | Perda ou acesso direto às evidências no filesystem local | Média | Muito alto | Permissões restritas, backup, retenção, antivírus e download autorizado |
| R25 | SMTP AUTH ou permissão de remetente bloquearem notificações | Média | Alto | Validar autenticação e `Send As` no Microsoft 365 antes de habilitar envios |
| R26 | Owner `VETORH` ser usado indevidamente pela aplicação | Baixa | Muito alto | Configurar somente `SGPD` no runtime e manter `VETORH` restrito a consultas administrativas explícitas |
| R27 | Consulta direta expor CPF completo ou dados excessivos | Média | Muito alto | Mascarar por padrão, autorização por finalidade e projeções mínimas |
| R28 | `INNER JOIN` omitir colaborador com cadastro relacionado incompleto | Média | Alto | Validar regra funcional, reconciliar contagens e tratar inconsistências explicitamente |
| R29 | Senha local continuar ativa indevidamente após vínculo com AD | Média | Alto | Desabilitar autenticação local comum após vinculação e restringir contas de contingência |
| R30 | Migrations não poderem criar objetos no schema `SGPD` | Mitigado em 2026-07-27 | Alto | `CREATE TABLE` sem `ADMIN OPTION` e quota de 500 MB em `PIMS_DATA` concedidos ao mesmo usuário `SGPD`; revisar SQL antes de aplicar |
| R31 | Oracle Client ausente ou incompatível impedir conexão em modo Thick | Baixa | Alto | Fixar Instant Client 19.28 no DEV, validar no readiness e falhar na inicialização sem expor segredo |
| R32 | Usuário autenticado consultar referências fora do futuro escopo de empresa/filial | Média | Alto | Definir papéis e escopos antes do MVP e adicionar permissão objetiva aos endpoints; manter CPF ausente das listagens |
