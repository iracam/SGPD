# Registro de Riscos

Riscos mitigados permanecem na matriz enquanto o controle precisar continuar
ativo. Riscos que deixaram de existir são movidos para a seção de encerrados.

| ID | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---:|---:|---|
| R01 | Acoplamento às tabelas internas do Senior | Alta | Alto | Contrato SQL homologado, objetos qualificados, testes de contrato e revisão a cada upgrade |
| R02 | Uso do owner `SGPD` pela aplicação ampliar impacto de falha ou credencial comprometida | Decisão aceita no DEV | Muito alto | `.env` 600, SQL centralizado, sem DDL no runtime, migrations revisadas, auditoria e reavaliação antes de outro ambiente |
| R03 | Dados de colaborador alterados após abertura | Alta | Alto | Snapshot imutável |
| R04 | Checklist alterado afetar histórico | Alta | Alto | Versionamento |
| R05 | Desconto indevido | Média | Muito alto | Pretensão, aprovação e segregação |
| R06 | Acesso indevido a documentos médicos | Média | Muito alto | Autorização por classe e setor |
| R07 | E-mails não enviados | Média | Médio | Fila, retry e painel de falhas |
| R08 | Responsável ausente | Alta | Médio | Múltiplos responsáveis de igual autoridade, validade explícita, fila e escalada |
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
| R21 | Vinculação ao AD associar a identidade errada ou duplicada | Mitigado em 2026-07-28 | Muito alto | Identidade pesquisada e revalidada por `objectGUID`, constraint única, confirmação administrativa, justificativa, auditoria e testes de duplicidade/conflito |
| R22 | Uso indevido do WhiteNoise para evidências ou uploads | Média | Muito alto | Restringir WhiteNoise a estáticos e usar storage privado para evidências |
| R23 | Ausência de CI/CD permitir validações locais inconsistentes | Média | Médio | Padronizar comandos locais e registrar evidências de testes |
| R25 | SMTP AUTH ou permissão de remetente bloquearem notificações | Mitigado em 2026-07-28 | Alto | SMTP AUTH e `Send As` validados com mensagem de prova aceita pelo Microsoft 365 |
| R26 | Owner `VETORH` ser usado indevidamente pela aplicação | Baixa | Muito alto | Configurar somente `SGPD` no runtime e manter `VETORH` restrito a consultas administrativas explícitas |
| R27 | Consulta direta expor CPF completo ou dados excessivos | Média | Muito alto | Excluir CPF das listagens, aplicar autorização por finalidade e manter projeções mínimas |
| R28 | `INNER JOIN` omitir colaborador com cadastro relacionado incompleto | Mitigado em 2026-07-28 | Alto | `LEFT JOIN` de centro de custo homologado por reconciliação global; contrato e contagens permanecem testados |
| R29 | Senha local continuar ativa indevidamente após ativação do login AD | Mitigado em 2026-07-28 | Alto | Backend local, redefinição administrativa, troca da própria senha e SPA usam a mesma política; contas comuns vinculadas são bloqueadas quando AD está ativo; importação usa senha inutilizável; fallback limitado a superusuário de contingência configurável e testado |
| R30 | Migrations não poderem criar objetos no schema `SGPD` | Mitigado em 2026-07-27 | Alto | `CREATE TABLE` e `CREATE SEQUENCE` sem `ADMIN OPTION`, quota de 500 MB e revisão do SQL; 25 migrations aplicadas e validadas |
| R31 | Oracle Client ausente ou incompatível impedir conexão em modo Thick | Baixa | Alto | Fixar Instant Client 19.28 no DEV, validar no readiness e falhar na inicialização sem expor segredo |
| R32 | Usuário autenticado consultar referências fora do escopo de empresa/filial | Mitigado em 2026-07-27 | Alto | Permissão `query_senior_references`, atribuição com validade e escopo, filtro de empresas e resposta `403`; CPF ausente das listagens |
| R33 | Vínculo AD administrativo ser confundido com autenticação AD homologada | Mitigado em 2026-07-28 | Alto | Chaves independentes para descoberta e autenticação, status explícito na API/UI, system check e comando de probe; ativação real permanece pendente e declarada |
| R35 | Chamada direta de service administrativo contornar a autorização do endpoint | Mitigado em 2026-07-28 | Muito alto | Permissão validada no próprio service e testes de negação sem mutação ou auditoria espúria |
| R36 | Operação em lote do ORM alterar ou excluir auditoria append-only | Mitigado em 2026-07-28 | Muito alto | `QuerySet.update()` e `QuerySet.delete()` bloqueados, além das proteções por instância |
| R37 | Desativações concorrentes removerem todos os superusuários ativos | Mitigado em 2026-07-28 | Alto | Lock pessimista dos superusuários ativos em ordem determinística e validação transacional do último ativo |
| R38 | Ampliação da superfície de API na migração introduzir endpoint sem autorização | Mitigado em 2026-07-28 | Muito alto | Endpoints são casca fina sobre services que revalidam permissão; cada endpoint possui teste de permissão negada |
| R39 | Troca obrigatória de senha temporária deixar de ser imposta na SPA/API | Mitigado em 2026-07-28 | Alto | Middleware devolve `403` tipado sob `/api/`, redireciona navegação direta para `/fe/senha` e possui testes dedicados |
| R41 | Portar SCSS desktop first do projeto de referência e inviabilizar o uso em telefone | Mitigado em 2026-07-28 | Médio | Consultas `max-width` proibidas em código novo pela ADR-028; conferência visual obrigatória nos cinco pontos de quebra ao encerrar cada fase de interface |
| R42 | Dependências npm ampliarem a superfície de cadeia de suprimento | Média | Médio | `package-lock.json` versionado, instalação por `npm ci`, atualização somente após revisão explícita e nenhum carregamento de CDN em runtime |
| R43 | Origem única exigida pela sessão com CSRF ser quebrada por proxy ou novo domínio | Baixa | Alto | Registrado na ADR-026; qualquer proxy reverso, domínio separado ou ambiente HML/PRD reabre a decisão junto com a ADR-014 |
| R44 | Atualização do PrimeNG para 22 ou superior reintroduzir exigência de chave de licença e aviso permanente na interface | Média | Médio | Versão fixada em 21, última sob MIT; atualização passa a exigir decisão de licenciamento e nova ADR, conforme ADR-027 |
| R45 | Dependências transitivas de desenvolvimento do Angular CLI incluírem vulnerabilidade moderada de path traversal no servidor estático Hono para Windows | Baixa no DEV atual | Médio | `npm audit --omit=dev` confirma zero vulnerabilidades de runtime; DEV homologado usa Debian; não executar `npm audit fix --force`, pois a correção proposta altera o Angular CLI de forma incompatível; revisar quando a cadeia Angular publicar atualização compatível |
| R46 | Falha de transporte, bind ou disponibilidade do AD impedir autenticação corporativa | Média | Alto | Escolha única de transporte; LDAPS e CA quando TLS estiver ativo; timeouts, erro genérico sem fallback local comum, probe operacional e superusuário local de contingência |
| R47 | Base ou filtro AD excessivamente amplo expor identidades ou permitir conta fora do público SGPD | Média | Muito alto | Base por OU, grupo obrigatório opcional, suporte a grupo aninhado, filtro fixo revisado, exclusão de conta desabilitada, paginação/limite e autorização administrativa |
| R48 | LDAP simples expor a credencial técnica e a senha dos usuários na rede | Decisão administrativa explícita | Muito alto | Opção exclusiva de SuperAdmin; warning permanente no check e na SPA; conta técnica somente leitura; mesma escolha visível para descoberta e login; recomendar TLS; nunca registrar credenciais |
| R49 | Configuração LDAP pela aplicação expor segredo, aceitar CA inválida ou ativar login sem contingência | Baixa | Muito alto | Acesso direto por `is_superuser`; senha Fernet nunca projetada; upload privado limitado e validado como CA X.509 vigente; hash; versão otimista; auditoria; ativação exige fingerprint de probe e SuperAdmin local utilizável; com TLS, exige CA válida |
| R50 | Setor com escopo ou escalada incorretos gerar tarefa indevida ou bloquear o processo | Média | Alto | Escopo explícito e não redundante, global exclusivo, cadeia de escalada sem ciclos, versão otimista, bloqueio pessimista ordenado do catálogo, service transacional e auditoria antes/depois; os nove setores cadastrados em 2026-07-29 permanecem com atributos provisórios e não devem alimentar o workflow antes da homologação funcional |
| R51 | Dois responsáveis do mesmo setor agirem simultaneamente e duplicarem transição, auditoria, e-mail ou efeito externo | Média | Alto | Mesma autoridade sem coordenador; transação atômica, lock ou versão no estado crítico, chave de idempotência, efeitos após commit e resposta com estado atualizado para quem perder a corrida |
| R52 | Associação de responsável exceder o escopo, sobreviver à desativação do setor ou usuário ou exceder a validade do papel | Média | Muito alto | Service bloqueia e revalida setor, usuário, papel e associação; escopo deve ser coberto pelo setor e pelo papel, e o período deve caber na atribuição do papel; autorização operacional exige ambos vigentes; constraints, versão otimista, revogação lógica e auditoria antes/depois |
| R53 | Confundir papel `DP` com responsabilidade pelo setor Departamento Pessoal e conceder abertura, liberação ou encerramento indevidos | Média | Muito alto | Conceitos independentes e cumulativos; `has_effective_role()` exige atribuição `DP` explícita, vigente e compatível com o escopo; SuperAdmin, grupo AD e associação de setor não concedem `DP`; cada transição revalida estado, prontidão e auditoria |

## Riscos encerrados

| ID | Risco | Encerramento |
|---|---|---|
| R34 | Runtime HTMX local ficar desatualizado ou divergir da origem oficial | Encerrado em 2026-07-28 após remoção do runtime na Fase G |
| R40 | Remover a interface server-side antes da SPA cobrir a função equivalente | Encerrado em 2026-07-28; a remoção ocorreu somente após a cobertura funcional da SPA |
