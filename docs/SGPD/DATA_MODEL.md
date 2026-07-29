# Modelo de Dados de Referência

## Estado do documento

Este é o modelo conceitual do produto. Na implementação atual, contas, o papel,
escopos, auditoria de contas, configuração técnica LDAP, setores, escopos de
setor, responsáveis, processo em rascunho, snapshot do colaborador e auditoria
da abertura possuem models e migrations. Os demais domínios serão detalhados e
implementados nos checkpoints das Fases 3 a 9; seus nomes abaixo não autorizam
criação antecipada de schema.

## 1. Princípios

- Usar chaves substitutas internas.
- Preservar chaves externas do Senior.
- Evitar exclusão física de dados utilizados em processos.
- Implementar versionamento de templates e regras.
- Copiar dados relevantes para snapshot.
- Separar dados cadastrais, operacionais, auditoria e integração.
- Não armazenar arquivos grandes diretamente no banco sem decisão explícita.
- Manter hash, metadados e vínculo do arquivo no banco.
- Não modelar nem replicar tabelas cadastrais do Senior no SGPD.
- Consultar referências do Senior por SQL somente leitura e persistir apenas o snapshot necessário ao processo.

## 2. Domínios principais

### Usuários e identidade

Usuários, e-mails, papéis funcionais e escopos pertencem ao SGPD e não são
obtidos do Senior.

#### SGPD_USER

- `ID`
- `USERNAME`
- `FIRST_NAME`
- `LAST_NAME`
- `EMAIL`
- `PASSWORD`
- `IS_ACTIVE`
- `IS_STAFF`
- `IS_SUPERUSER`
- `MUST_CHANGE_PASSWORD`
- `AD_IDENTIFIER`
- `AD_USERNAME`
- `AD_LINKED_AT`
- `AD_LINKED_BY_ID`
- `VERSION`

O vínculo AD exige simultaneamente identificador opaco, usuário, data e
administrador responsável. `AD_IDENTIFIER` é único e normalizado. O vínculo
usa o `objectGUID` do Active Directory convertido para UUID canônico; login e
e-mail são atributos informativos, não a chave. A mesma estrutura atende tanto
ao cadastro local com vínculo posterior quanto à criação explícita a partir do
AD, sem nova migration. Ativar o backend LDAP é uma decisão de configuração
independente do vínculo.

#### SGPD_ROLE

- `ID`
- `CODE`
- `NAME`
- `DESCRIPTION`
- `IS_ACTIVE`
- `VERSION`
- `CREATED_AT`
- `UPDATED_AT`
- relação com permissões delegáveis do Django.

Catálogo funcional fixo:

- `DP`.

Somente `DP` pode permanecer ativo, conforme `SGPD_CK_ROLE_ACTIVE_CODE`.
`RESPONSAVEL_SETOR` é um marcador derivado de vínculo vigente e não uma linha
atribuível do catálogo. Papéis legados permanecem inativos e fisicamente
preservados para rastreabilidade. SuperAdmin é o atributo técnico
`SGPD_USER.IS_SUPERUSER`, não um papel.

#### SGPD_ROLE_ASSIGN

- `ID`
- `USER_ID`
- `ROLE_ID`
- `SCOPE_TYPE`: `GLOBAL`, `COMPANY` ou `BRANCH`;
- `COMPANY_CODE`
- `BRANCH_CODE`
- `SCOPE_KEY`
- `VALID_FROM`
- `VALID_UNTIL`
- `IS_ACTIVE`
- `ASSIGNED_BY_ID`
- `ASSIGNED_AT`
- `REVOKED_BY_ID`
- `REVOKED_AT`

A atribuição é única por usuário, papel e chave de escopo. Toda nova
atribuição referencia `DP`. Empresa é obrigatória no escopo de empresa;
empresa e filial são obrigatórias no escopo de filial. A revogação é lógica,
com data, responsável e auditoria.

#### SGPD_ACCOUNT_AUDIT

- `ID`
- `UUID`
- `EVENT_TYPE`
- `ACTOR_ID`
- `TARGET_USER_ID`
- `ENTITY_TYPE`
- `ENTITY_ID`
- `OCCURRED_AT`
- `REASON`
- `CHANGES`
- `CORRELATION_ID`

Registra login, logout, falha de autenticação, criação e alteração de usuário,
senha, papel, atribuição, revogação e vínculo/desvínculo AD. O model não
permite alteração ou exclusão por usuários funcionais.

#### SGPD_LDAP_CONFIG

Singleton técnico, administrável somente por `IS_SUPERUSER=true`:

- switches independentes de descoberta e autenticação;
- URI, bind, bases, grupo, filtro, timeouts e limites;
- senha de bind cifrada, nunca projetada pela API;
- nome privado, hash SHA-256, subject, issuer e validade do bundle de CA;
- resultado, duração, ator e fingerprint do último teste de conexão;
- responsável, data de atualização e versão otimista.

O arquivo de CA fica fora do Oracle e do WhiteNoise, em
`SYSTEM_CONFIGURATION_STORAGE_PATH`. O registro não pode ser excluído pela
aplicação. A ativação de autenticação exige teste bem-sucedido cujo fingerprint
corresponda exatamente ao transporte, segredo, filtros, limites e certificado
vigentes.

### Referências do Senior não persistidas

Empresa, filial, tipo de colaborador, colaborador, cargo, centro de custo e situação funcional não terão models ou tabelas `REF_*`. Local de trabalho não faz parte do contrato.

A identidade externa utilizada nas consultas e no snapshot é:

```text
NUMEMP + CODFIL + TIPCOL + NUMCAD
```

Campos necessários para filtros e regras serão transportados como valores vindos da consulta e copiados para o snapshot. O SGPD não manterá foreign keys para objetos internos do Senior.

### Setores e responsáveis

#### SETOR_VALIDACAO

- `ID`
- `CODIGO`
- `NOME`
- `DESCRICAO`
- `ATIVO`
- `PRAZO_PADRAO_HORAS`
- `BLOQUEIA_PROCESSO`
- `PERMITE_VALOR`
- `EXIGE_EVIDENCIA`
- `SETOR_ESCALADA_ID`
- `CRIADO_EM`
- `ATUALIZADO_EM`
- `VERSAO`

O código é normalizado em maiúsculas e imutável após a criação. O setor pode
ser inativado, mas não excluído. `VERSAO` implementa concorrência otimista.
Um setor de escalada deve estar ativo, não pode ser o próprio setor e a cadeia
não pode formar ciclo.

#### SETOR_ESCOPO

- `ID`
- `SETOR_ID`
- `TIPO_ESCOPO`: `GLOBAL`, `COMPANY` ou `BRANCH`
- `EMPRESA_CODIGO`
- `FILIAL_CODIGO`
- `CHAVE_ESCOPO`

Existe ao menos um escopo por setor. Global não pode ser combinado com empresa
ou filial. Empresa cobre todas as suas filiais e, portanto, não pode coexistir
com uma filial redundante da mesma empresa. Os códigos são referências externas
sem foreign key ou cópia de cadastro do Senior.

#### SETOR_AUDITORIA

- `ID`
- `UUID`
- `TIPO_EVENTO`
- `ATOR_ID`
- `SETOR_ID`
- `OCORRIDO_EM`
- `JUSTIFICATIVA`
- `ALTERACOES_JSON`
- `CORRELATION_ID`

Registra criação, alteração, ativação e inativação. É append-only e preserva
estado anterior e posterior, inclusive escopos.

#### SETOR_RESPONSAVEL

- `ID`
- `SETOR_ID`
- `USUARIO_ID`
- `VALIDO_DE`
- `VALIDO_ATE`
- `ATIVO`
- `ATRIBUIDO_POR_ID`
- `ATRIBUIDO_EM`
- `ATUALIZADO_POR_ID`
- `ATUALIZADO_EM`
- `REVOGADO_POR_ID`
- `REVOGADO_EM`
- `VERSAO`

Não existe tipo de responsabilidade. Todos os responsáveis ativos do mesmo
setor possuem a mesma autoridade, recebem as mesmas notificações e podem
movimentar a tarefa. As capacidades decorrem do setor e do estado do processo,
sem flags individuais.

A associação é única por usuário e setor, usa validade com término exclusivo,
versão e revogação lógica. Não repete colunas organizacionais: herda todos os
escopos vigentes do próprio setor. Setor, usuários e associações são
bloqueados em ordem pelos services do agregado antes da mutação. Eventos de
associação, atualização e revogação reutilizam `SETOR_AUDITORIA`, com IDs
técnicos, estado anterior/posterior e motivo padronizado pelo servidor.

### Grupos de validação

#### GRUPO_VALIDACAO

- `ID`
- `CODIGO`
- `NOME`
- `DESCRICAO`
- `VERSAO`
- `ATIVO`
- `VALIDO_DE`
- `VALIDO_ATE`

#### GRUPO_VALIDACAO_SETOR

- `ID`
- `GRUPO_ID`
- `SETOR_ID`
- `OBRIGATORIO`
- `ORDEM_EXIBICAO`
- `PRAZO_ESPECIFICO_HORAS`
- `BLOQUEIO_PADRAO`

### Regras de aplicabilidade

#### REGRA_APLICABILIDADE

- `ID`
- `NOME`
- `PRIORIDADE`
- `EMPRESA_CODIGO`
- `FILIAL_CODIGO`
- `TIPO_COLABORADOR_CODIGO`
- `ESTRUTURA_CARGO_CODIGO`
- `CARGO_CODIGO`
- `CENTRO_CUSTO_CODIGO`
- `GRUPO_ID`
- `ATIVO`
- `VALIDO_DE`
- `VALIDO_ATE`

A regra poderá usar expressão declarativa em fase posterior.

### Templates

#### TEMPLATE_CHECKLIST

- `ID`
- `SETOR_ID`
- `NOME`
- `VERSAO`
- `ATIVO`
- `VALIDO_DE`
- `VALIDO_ATE`

#### TEMPLATE_CHECKLIST_ITEM

- `ID`
- `TEMPLATE_ID`
- `CODIGO`
- `PERGUNTA`
- `TIPO_RESPOSTA`
- `OBRIGATORIO`
- `BLOQUEIO`
- `EXIGE_EVIDENCIA`
- `PERMITE_PENDENCIA`
- `ORDEM_EXIBICAO`
- `CONFIG_JSON`

### Processo

#### PROCESSO_DEMISSIONAL

- `ID`
- `UUID`
- `NUMERO`
- `STATUS`
- `EMPRESA_CODIGO`
- `FILIAL_CODIGO`
- `TIPO_COLABORADOR_CODIGO`
- `COLABORADOR_MATRICULA`
- `GESTOR_USUARIO_ID`
- `GESTOR_NOME_SNAPSHOT`
- `GESTOR_EMAIL_SNAPSHOT`
- `ABERTO_POR_ID`
- `DATA_ABERTURA`
- `DATA_PREVISTA_DESLIGAMENTO`
- `DATA_LIMITE`
- `MOTIVO`
- `PRIORIDADE`
- `OBSERVACAO`
- `DATA_LIBERACAO`
- `LIBERADO_POR_ID`
- `DATA_ENCERRAMENTO`
- `ENCERRADO_POR_ID`
- `VERSAO_LOCK`

Estado implementado em `SGPD_OFFBOARDING_PROCESS`:

- usa `UUID` como identificador público; o formato do número funcional ainda
  não foi homologado e, portanto, `NUMERO` não foi antecipado;
- cria somente o estado `RASCUNHO`;
- `ACTIVE_EMPLOYEE_KEY` é anulável e única, formada pela identidade Senior; é
  preenchida enquanto o processo não estiver encerrado e será liberada apenas
  por transição futura auditada de cancelamento ou encerramento;
- preserva usuário, nome e e-mail históricos do gestor;
- possui versão, índices por estado/prazo, identidade/abertura e ator;
- rejeita `QuerySet.update()` e exclusão física; as futuras transições deverão
  alterar instâncias somente por services auditados.

#### PROCESSO_COLABORADOR_SNAPSHOT

- `ID`
- `PROCESSO_ID`
- `EMPRESA_CODIGO`
- `EMPRESA_NOME`
- `FILIAL_CODIGO`
- `FILIAL_NOME`
- `TIPO_COLABORADOR_CODIGO`
- `TIPO_COLABORADOR_DESCRICAO`
- `MATRICULA`
- `NOME`
- `CPF_MASCARADO`
- `CODIGO_AFASTAMENTO`
- `DESCRICAO_AFASTAMENTO`
- `DATA_AFASTAMENTO`
- `ESTRUTURA_CARGO_CODIGO`
- `CARGO_CODIGO`
- `CARGO`
- `CENTRO_CUSTO_CODIGO`
- `CENTRO_CUSTO`
- `DATA_ADMISSAO`
- `ORIGEM_ATUALIZADA_EM`
- `SITUACAO`
- `DADOS_EXTRAS_JSON`
- `CRIADO_EM`

Estado implementado em `SGPD_EMPLOYEE_SNAPSHOT`:

- relação um-para-um protegida com o processo;
- `FILIAL_NOME` corresponde à razão social retornada pelo contrato atual; o
  Senior não fornece um nome de empresa separado;
- registra `SOURCE_QUERIED_AT` além de `ORIGEM_ATUALIZADA_EM`;
- mantém CPF somente mascarado e não o projeta na API de abertura;
- rejeita alteração e exclusão por instância ou em lote.

#### PROCESSO_AUDITORIA

- `ID`
- `UUID`
- `PROCESSO_ID`
- `TIPO_EVENTO`
- `ATOR_ID`
- `OCORRIDO_EM`
- `DESCRICAO`
- `DADOS_JSON`
- `CORRELATION_ID`

`SGPD_PROCESS_AUDIT` é append-only. Neste incremento aceita
`PROCESS_OPENED` e registra apenas IDs técnicos, escopo, datas, prioridade e
estado, sem nome, e-mail ou CPF.

#### PROCESSO_SETOR

- `ID`
- `PROCESSO_ID`
- `SETOR_ID`
- `STATUS`
- `OBRIGATORIO`
- `BLOQUEIO`
- `SETOR_CODIGO_SNAPSHOT`
- `SETOR_NOME_SNAPSHOT`
- `TEMPLATE_VERSAO_ID`
- `DATA_LIMITE`
- `INICIADO_EM`
- `CONCLUIDO_EM`
- `CONCLUIDO_POR_ID`
- `OBSERVACAO`
- `VERSAO_LOCK`

Uma tarefa pertence ao setor e não possui um responsável individual. A
autorização operacional é derivada dos vínculos efetivos do setor no escopo
organizacional do processo, preservando a igualdade entre múltiplos
responsáveis. Os identificadores dos destinatários de uma futura notificação,
quando necessários, deverão ser registrados separadamente como resultado do
fan-out, sem se tornarem propriedade da tarefa.

#### PROCESSO_CHECKLIST_ITEM

- `ID`
- `PROCESSO_SETOR_ID`
- `TEMPLATE_ITEM_ID`
- `PERGUNTA_SNAPSHOT`
- `TIPO_RESPOSTA`
- `OBRIGATORIO`
- `BLOQUEIO`
- `EXIGE_EVIDENCIA`
- `RESPOSTA_JSON`
- `RESPONDIDO_POR_ID`
- `RESPONDIDO_EM`

### Pendências

#### PENDENCIA

- `ID`
- `UUID`
- `PROCESSO_ID`
- `PROCESSO_SETOR_ID`
- `CATEGORIA`
- `TIPO`
- `TITULO`
- `DESCRICAO`
- `STATUS`
- `BLOQUEIO`
- `DATA_IDENTIFICACAO`
- `DATA_LIMITE_REGULARIZACAO`
- `REGISTRADO_POR_ID`
- `DECISAO_FINAL`
- `DECIDIDO_POR_ID`
- `DECIDIDO_EM`

#### PENDENCIA_ITEM

- `ID`
- `PENDENCIA_ID`
- `CODIGO_ITEM`
- `DESCRICAO`
- `PATRIMONIO`
- `NUMERO_SERIE`
- `QUANTIDADE`
- `UNIDADE`
- `ESTADO_ITEM`
- `DADOS_EXTRAS_JSON`

#### PENDENCIA_VALOR

- `ID`
- `PENDENCIA_ID`
- `VALOR_INFORMADO`
- `VALOR_APURADO`
- `VALOR_CONTESTADO`
- `VALOR_APROVADO`
- `VALOR_PROCESSADO`
- `MOEDA`
- `JUSTIFICATIVA`
- `APROVADO_POR_ID`
- `APROVADO_EM`

#### PENDENCIA_DECISAO

- `ID`
- `PENDENCIA_ID`
- `TIPO_DECISAO`
- `DECISAO`
- `PARECER`
- `DECIDIDO_POR_ID`
- `DECIDIDO_EM`

### Evidências

#### EVIDENCIA

- `ID`
- `UUID`
- `PROCESSO_ID`
- `PROCESSO_SETOR_ID`
- `PENDENCIA_ID`
- `NOME_ORIGINAL`
- `NOME_ARMAZENADO`
- `MIME_TYPE`
- `TAMANHO_BYTES`
- `HASH_SHA256`
- `CAMINHO`
- `ENVIADO_POR_ID`
- `ENVIADO_EM`
- `CLASSIFICACAO`
- `ATIVO`

### Histórico e auditoria

#### PROCESSO_HISTORICO

- `ID`
- `PROCESSO_ID`
- `TIPO_EVENTO`
- `DESCRICAO`
- `USUARIO_ID`
- `DATA_EVENTO`
- `DADOS_JSON`

#### AUDITORIA_EVENTO

- `ID`
- `UUID`
- `USUARIO_ID`
- `DATA_EVENTO`
- `IP`
- `USER_AGENT`
- `ACAO`
- `ENTIDADE`
- `ENTIDADE_ID`
- `VALOR_ANTERIOR_JSON`
- `VALOR_POSTERIOR_JSON`
- `JUSTIFICATIVA`
- `CORRELATION_ID`

### Notificações

#### NOTIFICACAO

- `ID`
- `USUARIO_ID`
- `TIPO`
- `TITULO`
- `MENSAGEM`
- `LINK`
- `LIDA`
- `CRIADA_EM`
- `LIDA_EM`

#### FILA_EMAIL

- `ID`
- `DESTINATARIO`
- `ASSUNTO`
- `CORPO`
- `STATUS`
- `TENTATIVAS`
- `ULTIMO_ERRO`
- `CRIADO_EM`
- `ENVIADO_EM`

### Integração

#### INTEGRACAO_CONSULTA_EVENTO

- `ID`
- `TIPO_CONSULTA`
- `INICIADA_EM`
- `DURACAO_MS`
- `STATUS`
- `REGISTROS_LIDOS`
- `CODIGO_ERRO`
- `CORRELATION_ID`

Esse evento não armazena CPF, filtros pessoais, SQL com valores interpolados ou payload de resposta.

## 3. Índices recomendados

- status e data limite do processo;
- colaborador e data de abertura;
- empresa e filial;
- status e data limite das tarefas;
- status e bloqueio das pendências;
- identidade externa do colaborador (`empresa`, `filial`, `tipo`, `matrícula`);
- UUIDs públicos;
- correlation ID da auditoria.

## 4. Concorrência

Utilizar controle otimista com campo `VERSAO_LOCK` nas entidades críticas.

## 5. Exclusão

Evitar exclusão física de:

- processos;
- tarefas;
- pendências;
- decisões;
- valores;
- evidências;
- auditoria.

Cadastros poderão ser inativados.
