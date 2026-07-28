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
| R14 | Upload malicioso | Média | Alto | Validação de tipo e tamanho, nomes aleatórios e storage privado |
| R15 | Escopo crescer antes do MVP | Alta | Alto | Roadmap e checkpoints |
| R16 | Divergência futura da versão Python homologada | Baixa | Médio | Python 3.13 fixado no `pyproject.toml`, ambiente isolado e `uv.lock` versionado |
| R18 | Criação futura de HML ou PRD sem paridade com DEV | Baixa | Alto | Exigir nova decisão e inventário antes de ampliar ambientes |
| R19 | Exposição do `.env` local com credenciais | Média | Muito alto | Ignorar no Git, restringir permissões e nunca registrar valores em logs |
| R20 | Ferramentas Python globais com versões divergentes | Alta | Médio | Usar ambiente virtual e lockfile do projeto |
| R21 | Vinculação ao AD associar a identidade errada ou duplicada | Média | Muito alto | Identificador opaco normalizado e único, confirmação administrativa, justificativa, auditoria e teste de duplicidade |
| R22 | Uso indevido do WhiteNoise para evidências ou uploads | Média | Muito alto | Restringir WhiteNoise a estáticos e usar storage privado para evidências |
| R23 | Ausência de CI/CD permitir validações locais inconsistentes | Média | Médio | Padronizar comandos locais e registrar evidências de testes |
| R25 | SMTP AUTH ou permissão de remetente bloquearem notificações | Mitigado em 2026-07-28 | Alto | Credenciais atualizadas; SMTP AUTH e `Send As` validados com mensagem de prova aceita pelo Microsoft 365 |
| R26 | Owner `VETORH` ser usado indevidamente pela aplicação | Baixa | Muito alto | Configurar somente `SGPD` no runtime e manter `VETORH` restrito a consultas administrativas explícitas |
| R27 | Consulta direta expor CPF completo ou dados excessivos | Média | Muito alto | Mascarar por padrão, autorização por finalidade e projeções mínimas |
| R28 | `INNER JOIN` omitir colaborador com cadastro relacionado incompleto | Média | Alto | Validar regra funcional, reconciliar contagens e tratar inconsistências explicitamente |
| R29 | Senha local continuar ativa indevidamente após ativação futura do login AD | Média | Alto | Vínculo administrativo não ativa AD; na homologação do backend, desabilitar a senha local comum e restringir contas de contingência |
| R30 | Migrations não poderem criar objetos no schema `SGPD` | Mitigado em 2026-07-27 | Alto | `CREATE TABLE` e `CREATE SEQUENCE` sem `ADMIN OPTION`, quota de 500 MB e revisão do SQL; 23 migrations aplicadas e validadas |
| R31 | Oracle Client ausente ou incompatível impedir conexão em modo Thick | Baixa | Alto | Fixar Instant Client 19.28 no DEV, validar no readiness e falhar na inicialização sem expor segredo |
| R32 | Usuário autenticado consultar referências fora do escopo de empresa/filial | Mitigado em 2026-07-27 | Alto | Permissão `query_senior_references`, atribuição com validade e escopo, filtro de empresas e resposta `403`; CPF ausente das listagens |
| R33 | Vínculo AD administrativo ser confundido com autenticação AD homologada | Média | Alto | Aviso explícito na UI e documentação; não instalar backend LDAP nem desabilitar senha local sem contrato de endpoint, TLS, atributo e contingência |
| R34 | Runtime HTMX local ficar desatualizado ou divergir da origem oficial | Encerrado em 2026-07-28 | Médio | HTMX sai da stack pela ADR-025; o runtime é removido na Fase G da migração |
| R35 | Chamada direta de service administrativo contornar a autorização da view | Mitigado em 2026-07-28 | Muito alto | Permissão validada no próprio service e testes de negação sem mutação ou auditoria espúria |
| R36 | Operação em lote do ORM alterar ou excluir auditoria append-only | Mitigado em 2026-07-28 | Muito alto | `QuerySet.update()` e `QuerySet.delete()` bloqueados, além das proteções por instância |
| R37 | Desativações concorrentes removerem todos os superusuários ativos | Mitigado em 2026-07-28 | Alto | Lock pessimista dos superusuários ativos em ordem determinística e validação transacional do último ativo |
| R38 | Ampliação da superfície de API na migração introduzir endpoint sem autorização | Alta | Muito alto | Endpoints são casca fina sobre services que já revalidam permissão; teste obrigatório de permissão negada por endpoint antes de remover a UI server-side |
| R39 | Troca obrigatória de senha temporária deixar de ser imposta sem o redirecionamento server-side | Média | Alto | Middleware devolve `403` com código próprio sob `/api/`, com teste dedicado, e a SPA conduz à tela de troca |
| R40 | Remover a interface server-side antes da SPA cobrir a função equivalente | Média | Alto | Sequência fixa das fases, com remoção somente na Fase G, após as telas correspondentes estarem em operação |
| R41 | Portar SCSS desktop first do projeto de referência e inviabilizar o uso em telefone | Alta | Médio | Consultas `max-width` proibidas em código novo pela ADR-028; conferência visual obrigatória nos cinco pontos de quebra ao encerrar cada fase de interface |
| R42 | Dependências npm ampliarem a superfície de cadeia de suprimento | Média | Médio | `package-lock.json` versionado, instalação por `npm ci`, atualização somente após revisão explícita e nenhum carregamento de CDN em runtime |
| R43 | Origem única exigida pela sessão com CSRF ser quebrada por proxy ou novo domínio | Baixa | Alto | Registrado na ADR-026; qualquer proxy reverso, domínio separado ou ambiente HML/PRD reabre a decisão junto com a ADR-014 |
| R44 | Atualização do PrimeNG para 22 ou superior reintroduzir exigência de chave de licença e aviso permanente na interface | Média | Médio | Versão fixada em 21, última sob MIT; atualização passa a exigir decisão de licenciamento e nova ADR, conforme ADR-027 |
