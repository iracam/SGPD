# Requisitos

## 1. Requisitos funcionais

### RF-001 — Autenticação

O sistema deverá autenticar usuários preferencialmente por Active Directory/LDAP.

### RF-002 — Perfis e permissões

O sistema deverá controlar permissões por papel e escopo organizacional.

### RF-003 — Cadastro de setores

O sistema deverá permitir cadastro de setores responsáveis por validações.

Campos mínimos:

- código;
- nome;
- descrição;
- situação;
- prazo padrão;
- bloqueia conclusão;
- permite lançar valores;
- exige evidência;
- responsável de escalada;
- empresas atendidas;
- filiais atendidas.

### RF-004 — Cadastro de responsáveis

Cada setor poderá possuir um ou mais responsáveis.

Campos mínimos:

- usuário;
- nome;
- e-mail;
- setor;
- principal ou substituto;
- data de início;
- data de término;
- escopo por empresa;
- escopo por filial;
- recebe notificações;
- pode concluir;
- pode lançar pendência;
- pode lançar valores;
- pode aprovar exceções.

### RF-005 — Integração de empresas

O sistema deverá consultar ou sincronizar empresas do Senior HCM.

### RF-006 — Integração de filiais

Ao selecionar uma empresa, o sistema deverá listar apenas filiais relacionadas.

### RF-007 — Integração de tipos de colaborador

Ao selecionar empresa e filial, o sistema deverá listar os tipos de colaborador aplicáveis.

### RF-008 — Integração de colaboradores

Ao selecionar empresa, filial e tipo, o sistema deverá listar colaboradores compatíveis.

### RF-009 — Abertura de processo

O DP deverá abrir um processo informando:

- empresa;
- filial;
- tipo de colaborador;
- colaborador;
- data de abertura automática;
- data prevista de desligamento;
- data limite;
- motivo;
- prioridade;
- grupos de validação;
- observações.

### RF-010 — Snapshot do colaborador

No momento da abertura, o sistema deverá copiar para o processo:

- identificadores externos;
- matrícula;
- nome;
- cargo;
- local;
- centro de custo;
- gestor;
- e-mail;
- data de admissão;
- situação;
- empresa;
- filial;
- tipo de colaborador.

Alterações posteriores no Senior não deverão alterar o snapshot.

### RF-011 — Grupos de validação

O sistema deverá permitir cadastrar grupos de validação compostos por setores.

### RF-012 — Aplicabilidade automática

O sistema poderá sugerir grupos com base em:

- empresa;
- filial;
- tipo de colaborador;
- cargo;
- centro de custo;
- local;
- categoria;
- vínculo;
- outros atributos disponíveis.

### RF-013 — Alteração manual do grupo

O DP poderá incluir ou remover setores, com justificativa obrigatória.

### RF-014 — Templates de checklist

Cada setor poderá ter um ou mais templates de checklist.

### RF-015 — Versionamento

Templates e itens deverão ser versionados.

### RF-016 — Geração de tarefas

Ao iniciar o processo, o sistema deverá criar uma tarefa para cada setor aplicável.

### RF-017 — Processamento paralelo

As tarefas dos setores deverão ocorrer em paralelo.

### RF-018 — Respostas de checklist

Os itens poderão aceitar:

- sim/não;
- texto;
- número;
- data;
- seleção;
- múltipla seleção;
- arquivo;
- confirmação obrigatória.

### RF-019 — Pendências

O sistema deverá permitir criar múltiplas pendências por setor.

### RF-020 — Tipos de pendência

Exemplos:

- material;
- ferramenta;
- equipamento;
- documento;
- acesso;
- exame;
- atividade;
- valor;
- veículo;
- patrimônio;
- contrato;
- outro.

### RF-021 — Evidências

O sistema deverá permitir anexar arquivos às tarefas e pendências.

### RF-022 — Hash de evidências

O sistema deverá calcular e armazenar hash dos arquivos.

### RF-023 — Situação da pendência

A pendência deverá possuir fluxo próprio.

Estados sugeridos:

- aberta;
- comunicada;
- reconhecida;
- contestada;
- em regularização;
- regularizada;
- encaminhada;
- aprovada;
- rejeitada;
- abonada;
- encerrada.

### RF-024 — Classificação de bloqueio

Setores, itens e pendências poderão ser:

- informativos;
- não bloqueantes;
- bloqueantes;
- bloqueantes até decisão.

### RF-025 — Pretensão de cobrança

Áreas poderão informar valor estimado, mas não aplicar desconto diretamente.

### RF-026 — Aprovação de valores

O sistema deverá registrar:

- valor informado;
- valor apurado;
- valor contestado;
- valor aprovado;
- valor efetivamente processado;
- justificativa.

### RF-027 — Notificações

O sistema deverá enviar notificações por e-mail e no painel.

### RF-028 — Escaladas

O sistema deverá escalar tarefas próximas do vencimento ou vencidas.

### RF-029 — Liberação final

Somente o DP poderá liberar o processo para rescisão.

### RF-030 — Condições de liberação

A liberação deverá verificar:

- tarefas obrigatórias concluídas;
- pendências bloqueantes decididas;
- aprovações concluídas;
- evidências obrigatórias presentes;
- ausência de inconsistência crítica.

### RF-031 — Cancelamento

O DP poderá cancelar um processo com justificativa.

### RF-032 — Reabertura

A reabertura deverá exigir permissão especial e registrar motivo.

### RF-033 — Histórico

Toda ação relevante deverá gerar evento de auditoria.

### RF-034 — Painel do DP

O painel deverá exibir:

- processos por status;
- processos vencidos;
- processos próximos do prazo;
- pendências abertas;
- setores atrasados;
- valores em análise.

### RF-035 — Painel do setor

O painel deverá exibir:

- tarefas pendentes;
- tarefas vencidas;
- tarefas por empresa;
- tarefas por filial;
- processos críticos.

### RF-036 — Relatórios

Relatórios mínimos:

- tempo médio do processo;
- tempo médio por setor;
- pendências por categoria;
- processos por empresa;
- processos vencidos;
- setores com maior atraso;
- valores informados e aprovados;
- processos liberados por período.

### RF-037 — Integração futura com Senior

O sistema deverá estar preparado para registrar:

- número da rescisão;
- data de processamento;
- status da rescisão;
- valor efetivamente processado;
- retorno de encerramento.

## 2. Requisitos não funcionais

### RNF-001 — Banco

Oracle será o banco padrão do sistema.

### RNF-002 — Owner exclusivo

O SGPD utilizará schema/owner exclusivo.

### RNF-003 — Separação de credenciais

A aplicação não utilizará o owner para operação diária.

### RNF-004 — Segurança

Aplicação deverá seguir princípios de menor privilégio.

### RNF-005 — Auditoria

Eventos críticos não poderão ser apagados por usuários funcionais.

### RNF-006 — Desempenho

Listagens principais devem responder em tempo aceitável sob carga corporativa.

### RNF-007 — Disponibilidade

A aplicação deverá suportar operação durante o horário administrativo, com rotinas monitoradas.

### RNF-008 — Compatibilidade

A interface deverá funcionar nos navegadores corporativos homologados.

### RNF-009 — Observabilidade

Aplicação deverá produzir logs estruturados, métricas e alertas de falha.

### RNF-010 — LGPD

Dados pessoais devem ser exibidos conforme necessidade e perfil.

### RNF-011 — Backup

Banco e arquivos deverão fazer parte da política corporativa de backup.

### RNF-012 — Idempotência

Rotinas de sincronização deverão poder ser repetidas sem duplicar dados.

### RNF-013 — Versionamento

Regras, templates e documentos devem preservar histórico.

### RNF-014 — Testes

Regras críticas deverão possuir testes automatizados.

### RNF-015 — Documentação

Toda integração e regra de negócio deverá ser documentada.
