# Integração Senior HCM e Oracle

## 1. Objetivo

Utilizar dados do Senior HCM para abastecer os cadastros de referência do SGPD sem escrever diretamente nas tabelas internas do produto.

## 2. Fonte oficial

O Senior HCM permanece como fonte oficial de:

- empresas;
- filiais;
- tipos de colaborador;
- colaboradores;
- cargos;
- locais;
- centros de custo;
- gestores;
- situação do vínculo;
- dados necessários ao processo de rescisão.

## 3. Schema proposto

```text
SENIOR_OWNER
    Dados internos do Senior HCM

HCM_INTEGRACAO
    Views controladas para leitura

SGPD_OWNER
    Estrutura do SGPD

SGPD_APP
    Usuário de execução da aplicação

SGPD_SYNC
    Usuário de sincronização
```

## 4. Privilégios

### SGPD_OWNER

- criar e alterar objetos do SGPD;
- executar migrations;
- não ser utilizado pela aplicação.

### SGPD_APP

- `SELECT`, `INSERT`, `UPDATE` e `DELETE` somente nos objetos necessários;
- execução de procedures autorizadas;
- sem `CREATE TABLE`;
- sem leitura direta das tabelas do Senior.

### SGPD_SYNC

- `SELECT` nas views de integração;
- escrita nas tabelas `REF_*` do SGPD;
- sem escrita no Senior.

## 5. Views sugeridas

- `VW_SGPD_EMPRESAS`
- `VW_SGPD_FILIAIS`
- `VW_SGPD_TIPOS_COLABORADOR`
- `VW_SGPD_COLABORADORES`
- `VW_SGPD_CARGOS`
- `VW_SGPD_LOCAIS`
- `VW_SGPD_CENTROS_CUSTO`
- `VW_SGPD_GESTORES`
- `VW_SGPD_SITUACOES`

## 6. Contrato mínimo das views

### VW_SGPD_EMPRESAS

- `COD_EMPRESA`
- `NOME_EMPRESA`
- `ATIVO`
- `DT_ATUALIZACAO`

### VW_SGPD_FILIAIS

- `COD_EMPRESA`
- `COD_FILIAL`
- `NOME_FILIAL`
- `ATIVO`
- `DT_ATUALIZACAO`

### VW_SGPD_TIPOS_COLABORADOR

- `COD_EMPRESA`
- `COD_FILIAL`
- `COD_TIPO`
- `DESCRICAO`
- `ATIVO`
- `DT_ATUALIZACAO`

### VW_SGPD_COLABORADORES

- `COD_EMPRESA`
- `COD_FILIAL`
- `COD_TIPO`
- `MATRICULA`
- `NOME`
- `CPF`
- `EMAIL`
- `COD_CARGO`
- `CARGO`
- `COD_LOCAL`
- `LOCAL`
- `COD_CENTRO_CUSTO`
- `CENTRO_CUSTO`
- `MATRICULA_GESTOR`
- `NOME_GESTOR`
- `DATA_ADMISSAO`
- `COD_SITUACAO`
- `SITUACAO`
- `ATIVO`
- `DT_ATUALIZACAO`

## 7. Estratégia de sincronização

### Carga inicial

- ler todas as views;
- inserir registros locais;
- registrar execução;
- validar contagens;
- gerar relatório de inconsistências.

### Carga incremental

- usar `DT_ATUALIZACAO` quando confiável;
- usar hash dos campos relevantes;
- atualizar somente alterações;
- inativar registros não mais disponíveis;
- nunca excluir referência já usada.

### Reconciliação periódica

Executar uma carga completa em periodicidade definida para corrigir divergências.

## 8. Idempotência

A chave de negócio deve impedir duplicidade.

Exemplo para colaborador:

```text
COD_EMPRESA + COD_FILIAL + COD_TIPO + MATRICULA
```

## 9. Snapshot

No início do processo:

1. consultar `REF_COLABORADOR`;
2. validar se está ativo ou elegível;
3. copiar todos os dados necessários;
4. registrar versão e data da referência;
5. impedir alteração automática do snapshot.

## 10. Escrita no Senior

Não deve ocorrer no MVP.

Integração futura poderá usar:

- web service oficial;
- API;
- procedure homologada;
- tabela de integração fornecida pelo fornecedor;
- fila intermediária.

Qualquer escrita deve possuir:

- contrato;
- idempotência;
- log;
- retry;
- resposta;
- correlação;
- homologação.

## 11. Falhas

Em caso de falha de sincronização:

- preservar os últimos dados válidos;
- registrar execução com erro;
- permitir reprocessamento;
- alertar administradores;
- impedir abertura apenas quando a falha tornar o cadastro inconsistente.

## 12. Segurança

- mascarar CPF quando não necessário;
- nunca registrar senha;
- usar conexão TLS conforme ambiente;
- rotacionar credenciais;
- limitar grants;
- auditar consultas administrativas;
- não expor nomes de tabelas internas do Senior na UI.

## 13. Itens a levantar antes da implementação

- versão exata do Senior HCM;
- owner atual;
- tabelas ou views homologadas;
- chaves de empresa, filial, tipo e colaborador;
- regra de colaborador ativo;
- origem do gestor;
- origem do e-mail;
- timezone;
- charset;
- disponibilidade de `DT_ATUALIZACAO`;
- política de acesso ao Oracle;
- política de criação de views;
- ambiente de homologação;
- possibilidade de web services oficiais.
