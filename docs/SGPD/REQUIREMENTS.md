# Requisitos

## Estado do documento

Estes requisitos definem o comportamento alvo do produto. O uso do futuro
indica requisito ainda não implementado, não decisão pendente. A cobertura
atual e a fase autorizada estão em `CHECKPOINT.md`.

## 1. Requisitos funcionais

### RF-001 — Autenticação

Todos os usuários, inclusive gestores, deverão ser cadastrados no SGPD com nome, e-mail, situação e papéis.

O SGPD deverá preservar autenticação local para contas não vinculadas e
contingência administrativa. Cada cadastro poderá ser vinculado a uma conta do
Active Directory para autenticação corporativa com uma única senha.

O Senior HCM não será fonte de usuários, gestores, e-mails, papéis ou permissões.

A manutenção deverá:

- exigir nome, sobrenome, login e e-mail únicos quando aplicável;
- permitir criação manual de conta local sem justificativa digitada, mantendo
  ator, origem e motivo operacional padronizado na auditoria;
- permitir designar um papel inicial e seu escopo no mesmo cadastro manual;
  quando informado, conta e atribuição deverão ser gravadas atomicamente,
  exigindo simultaneamente as permissões de manter usuários e papéis;
- não exigir justificativa digitada para criar, reativar ou atualizar uma
  atribuição de papel, preservando ator, escopo e motivo operacional
  padronizado na auditoria; a revogação continuará exigindo justificativa;
- emitir logs estruturados no recebimento e na conclusão da designação, usando
  somente IDs técnicos, escopo, resultado e correlation ID;
- permitir ativação e desativação sem exclusão física;
- exigir senha temporária forte e troca no próximo acesso quando configurado;
- impedir que o administrador desative a própria conta;
- preservar ao menos um superusuário ativo de contingência;
- auditar login, logout, falha, criação, alteração e redefinição de senha.

O vínculo administrativo com o AD deverá usar identificador opaco único,
usuário do diretório, data, administrador responsável e justificativa. O
`objectGUID` será a chave estável; e-mail não poderá ser usado como chave.

A administração deverá permitir:

- cadastrar uma conta local e vinculá-la posteriormente após consulta ao AD;
- consultar usuários e grupos por busca paginada e limitada;
- restringir a consulta por OU e por associação direta ou aninhada a grupo;
- criar explicitamente uma conta local já vinculada a uma identidade
  selecionada no AD;
- não exigir justificativa digitada para essa importação, pois a origem, o
  ator, o `objectGUID` e o motivo padronizado são registrados automaticamente
  na auditoria;
- detectar conflito de identidade, login e e-mail sem mesclar pessoas
  automaticamente;
- rejeitar provisionamento implícito durante o login.

Quando a autenticação AD estiver habilitada, contas comuns vinculadas não
poderão fazer fallback para senha local. Papéis, permissões e escopos
continuarão exclusivamente no SGPD e não serão importados de grupos AD. Um
superusuário local de contingência deverá ser preservado e testado. A API e a
SPA deverão bloquear definição, redefinição e troca de senha local nessas
contas, salvo a contingência configurada. Enquanto a autenticação AD estiver
desligada, a senha local poderá ser definida para testes controlados.

A configuração técnica de LDAP e autenticação deverá:

- ser visível e mutável somente por conta ativa com `IS_SUPERUSER=true`,
  criada por `createsuperuser` ou pelo bootstrap administrativo;
- não ser delegável por papel funcional;
- permitir editar transporte, bind, bases, grupo, filtros, limites e switches;
- nunca devolver a senha de bind pela API e mantê-la cifrada em repouso;
- aceitar upload limitado de certificado ou bundle X.509 de CA em storage
  privado, com validação de estrutura, finalidade, validade e hash SHA-256;
- validar o contrato sem persistir e testar bind e RootDSE sem listar pessoas;
- aplicar uma única escolha de transporte a descoberta, busca, importação,
  vínculo e login;
- montar LDAPS automaticamente e exigir CA válida quando TLS estiver ativo;
- permitir LDAP simples quando TLS estiver desativado por decisão explícita do
  SuperAdmin, exibindo aviso permanente de que a credencial técnica e as
  senhas dos usuários trafegam sem criptografia;
- exigir probe da mesma configuração e SuperAdmin local com senha utilizável
  antes de ativar o login AD;
- usar controle otimista e auditar alterações, upload e testes de conexão.

### RF-002 — Perfis e permissões

O sistema deverá controlar permissões por papel e escopo organizacional.

Os escopos iniciais serão global, empresa e filial. Atribuições deverão possuir
validade, revogação lógica, responsável e auditoria. Permissões provenientes de
papéis deverão respeitar o escopo; permissões diretas serão globais.

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

O responsável deverá referenciar um usuário cadastrado no SGPD. Nome e e-mail virão do perfil desse usuário.

Campos mínimos:

- usuário;
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

O sistema deverá consultar empresas diretamente no Senior HCM por SQL somente leitura.

Não serão criados models Django nem tabelas locais `REF_*` para dados cadastrais do Senior.

### RF-006 — Integração de filiais

Ao selecionar uma empresa, o sistema deverá consultar e listar apenas filiais relacionadas, usando parâmetros vinculados.

### RF-007 — Integração de tipos de colaborador

Ao selecionar empresa e filial, o sistema deverá consultar os tipos de colaborador aplicáveis diretamente no Senior.

### RF-008 — Integração de colaboradores

Ao selecionar empresa, filial e tipo, o sistema deverá consultar colaboradores compatíveis diretamente no Senior.

A consulta deverá:

- usar somente `SELECT`;
- usar nomes de objetos qualificados pelo schema `VETORH`;
- considerar elegível o colaborador com `R034FUN.SITAFA <> 7`;
- usar bind variables para filtros;
- possuir paginação e limite;
- não expor CPF completo em listagens;
- ficar encapsulada em uma camada de consulta, sem models para objetos do Senior.

### RF-009 — Abertura de processo

O DP deverá abrir um processo informando:

- empresa;
- filial;
- tipo de colaborador;
- colaborador;
- gestor imediato cadastrado no SGPD;
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
- centro de custo;
- data de admissão;
- data de atualização da origem (`R034FUN.USU_DATALT`);
- situação;
- empresa;
- filial;
- tipo de colaborador.

Alterações posteriores no Senior não deverão alterar o snapshot.

O snapshot é uma entidade do SGPD e não contradiz a ausência de models para referências do Senior.

O gestor é uma atribuição do processo, selecionada entre usuários cadastrados no SGPD. Nome e e-mail do gestor deverão ser preservados historicamente na abertura sem consultar o Senior.

### RF-011 — Grupos de validação

O sistema deverá permitir cadastrar grupos de validação compostos por setores.

### RF-012 — Aplicabilidade automática

O sistema poderá sugerir grupos com base em:

- empresa;
- filial;
- tipo de colaborador;
- cargo;
- centro de custo;
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

No DEV, a aplicação utilizará o owner `SGPD` para operação diária e migrations. Não será criado outro usuário Oracle para o SGPD neste ambiente.

Essa exceção não autoriza o uso do owner `VETORH` nem qualquer escrita nos objetos do Senior.

### RNF-004 — Segurança

A aplicação deverá seguir princípios de menor privilégio nas integrações. O risco adicional dos privilégios amplos do owner `SGPD` no DEV será aceito e compensado por revisão de SQL, ausência de DDL em runtime, secrets protegidos e testes.

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

O banco deverá fazer parte da política corporativa de backup.

### RNF-012 — Consultas sem efeitos colaterais

Consultas ao Senior deverão poder ser repetidas sem alterar dados no Senior ou no SGPD. A criação do snapshot ocorrerá somente no caso de uso transacional de abertura do processo.

### RNF-013 — Versionamento

Regras, templates e documentos devem preservar histórico.

### RNF-014 — Testes

Regras críticas deverão possuir testes automatizados.

### RNF-015 — Documentação

Toda integração e regra de negócio deverá ser documentada.
