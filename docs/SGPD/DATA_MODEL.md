# Modelo de Dados Inicial

## 1. Princípios

- Usar chaves substitutas internas.
- Preservar chaves externas do Senior.
- Evitar exclusão física de dados utilizados em processos.
- Implementar versionamento de templates e regras.
- Copiar dados relevantes para snapshot.
- Separar dados cadastrais, operacionais, auditoria e integração.
- Não armazenar arquivos grandes diretamente no banco sem decisão explícita.
- Manter hash, metadados e vínculo do arquivo no banco.

## 2. Domínios principais

### Referências integradas

- `REF_EMPRESA`
- `REF_FILIAL`
- `REF_TIPO_COLABORADOR`
- `REF_COLABORADOR`
- `REF_CARGO`
- `REF_LOCAL`
- `REF_CENTRO_CUSTO`
- `REF_GESTOR`

Campos comuns:

- `ID`
- `CODIGO_EXTERNO`
- `DESCRICAO`
- `ATIVO`
- `DT_ATUALIZACAO_ORIGEM`
- `DT_SINCRONIZACAO`
- `HASH_ORIGEM`
- `DADOS_EXTRAS_JSON`

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

#### SETOR_RESPONSAVEL

- `ID`
- `SETOR_ID`
- `USUARIO_ID`
- `EMAIL`
- `TIPO_RESPONSABILIDADE`
- `EMPRESA_ID`
- `FILIAL_ID`
- `DATA_INICIO`
- `DATA_FIM`
- `RECEBE_NOTIFICACAO`
- `PODE_CONCLUIR`
- `PODE_LANCAR_PENDENCIA`
- `PODE_LANCAR_VALOR`
- `PODE_APROVAR_EXCECAO`
- `ATIVO`

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
- `EMPRESA_ID`
- `FILIAL_ID`
- `TIPO_COLABORADOR_ID`
- `CARGO_ID`
- `LOCAL_ID`
- `CENTRO_CUSTO_ID`
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
- `EMPRESA_ID`
- `FILIAL_ID`
- `TIPO_COLABORADOR_ID`
- `COLABORADOR_ID`
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

#### PROCESSO_COLABORADOR_SNAPSHOT

- `ID`
- `PROCESSO_ID`
- `EMPRESA_CODIGO`
- `EMPRESA_NOME`
- `FILIAL_CODIGO`
- `FILIAL_NOME`
- `TIPO_COLABORADOR_CODIGO`
- `MATRICULA`
- `NOME`
- `CPF_MASCARADO`
- `CARGO`
- `LOCAL`
- `CENTRO_CUSTO`
- `GESTOR`
- `EMAIL`
- `DATA_ADMISSAO`
- `SITUACAO`
- `DADOS_EXTRAS_JSON`
- `CRIADO_EM`

#### PROCESSO_SETOR

- `ID`
- `PROCESSO_ID`
- `SETOR_ID`
- `STATUS`
- `OBRIGATORIO`
- `BLOQUEIO`
- `RESPONSAVEL_ID`
- `DATA_LIMITE`
- `INICIADO_EM`
- `CONCLUIDO_EM`
- `CONCLUIDO_POR_ID`
- `OBSERVACAO`
- `VERSAO_LOCK`

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

#### INTEGRACAO_EXECUCAO

- `ID`
- `ROTINA`
- `INICIADA_EM`
- `FINALIZADA_EM`
- `STATUS`
- `REGISTROS_LIDOS`
- `REGISTROS_INSERIDOS`
- `REGISTROS_ATUALIZADOS`
- `REGISTROS_INATIVADOS`
- `ERROS`

#### INTEGRACAO_ERRO

- `ID`
- `EXECUCAO_ID`
- `CHAVE_ORIGEM`
- `MENSAGEM`
- `DETALHE`
- `CRIADO_EM`

## 3. Índices recomendados

- status e data limite do processo;
- colaborador e data de abertura;
- empresa e filial;
- status e data limite das tarefas;
- status e bloqueio das pendências;
- chaves externas das tabelas de referência;
- hash de origem;
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
