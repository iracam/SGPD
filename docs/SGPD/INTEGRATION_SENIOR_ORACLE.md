# Integração Senior HCM e Oracle

## 1. Objetivo

Consultar dados cadastrais do Senior HCM diretamente no Oracle, em tempo real e somente por `SELECT`, sem escrever nos objetos do Senior e sem replicar referências em models ou tabelas `REF_*` do SGPD.

## 2. Decisão de acesso

- o Senior HCM permanece como fonte oficial;
- a conexão Oracle do SGPD acessa objetos `VETORH` no mesmo serviço;
- os nomes dos objetos são qualificados pelo schema;
- o acesso ocorre por SQL parametrizado em um repository/service chamado pelas views Django;
- não serão criados models Django, inclusive `managed = False`, para objetos do Senior;
- não serão criadas views Oracle locais nesta etapa;
- nenhum dado consultado é persistido até a abertura do processo;
- na abertura, o SGPD cria seu próprio snapshot histórico e auditável.

O termo “view local” neste projeto identifica a view da aplicação que consome a camada de consulta. O SQL e as credenciais não devem ficar na view de apresentação.

## 3. Ambiente validado em 2026-07-27

- Oracle Database 19c Enterprise Edition, versão 19.15.0.0.0;
- Oracle Instant Client 19.28;
- SQLcl local 26.1;
- serviço configurado no `.env` acessível;
- sessão do owner do SGPD confirmada como `SGPD`;
- schema de origem confirmado como `VETORH`;
- conexão salva `DEV@VETORH` no MCP aponta para um serviço não registrado e não foi usada na validação final;
- a conexão separada configurada com o owner `VETORH` funciona, mas é administrativa e não deve ser usada pela aplicação.

O `.env` real usa hoje o owner `SGPD`. Isso é suficiente para descoberta e migrations controladas, mas não homologa seu uso como usuário de runtime. Antes da aplicação, deve existir um usuário operacional separado, com grants mínimos.

## 4. Objetos e grants confirmados

Foram confirmados grants diretos `SELECT`, concedidos por `VETORH` a `SGPD`, nos seguintes objetos válidos:

| Objeto | Tipo | Grant |
|---|---|---|
| `VETORH.R010SIT` | `TABLE` | `SELECT` |
| `VETORH.R018CCU` | `TABLE` | `SELECT` |
| `VETORH.R024CAR` | `TABLE` | `SELECT` |
| `VETORH.R030FIL` | `TABLE` | `SELECT` |
| `VETORH.R034FUN` | `TABLE` | `SELECT` |

A consulta de colaboradores foi compilada e executada pela sessão `SGPD`, retornando uma linha no probe limitado. Nenhum DML ou DDL foi executado.

## 5. Contrato preliminar da consulta

### Chave do colaborador

```text
NUMEMP + CODFIL + TIPCOL + NUMCAD
```

### Mapeamento validado

| Campo lógico | Origem |
|---|---|
| empresa | `R034FUN.NUMEMP` |
| filial | `R034FUN.CODFIL` |
| razão social | `R030FIL.RAZSOC` |
| tipo do colaborador | `R034FUN.TIPCOL` |
| matrícula | `R034FUN.NUMCAD` |
| nome | `R034FUN.NOMFUN` |
| CPF | `R034FUN.NUMCPF` |
| data de admissão | `R034FUN.DATADM` |
| código de afastamento | `R034FUN.SITAFA` |
| descrição do afastamento | `R010SIT.DESSIT` |
| data de afastamento | `R034FUN.DATAFA` |
| estrutura de cargo | `R034FUN.ESTCAR` |
| código de cargo | `R034FUN.CODCAR` |
| descrição do cargo | `R024CAR.TITCAR` |
| centro de custo | `R034FUN.CODCCU` |
| descrição do centro de custo | `R018CCU.NOMCCU` |
| data de atualização da origem | `R034FUN.USU_DATALT` |

`R034FUN.USU_DATALT` foi validada como coluna Oracle `DATE`, anulável, com registros preenchidos. Ela deve ser retornada como data e preservada no snapshot para rastreabilidade da versão cadastral consultada. Como o acesso é online, esse campo não será usado para carga incremental.

### Relações validadas

```text
R034FUN.SITAFA = R010SIT.CODSIT
R034FUN.(NUMEMP, CODFIL) = R030FIL.(NUMEMP, CODFIL)
R034FUN.(ESTCAR, CODCAR) = R024CAR.(ESTCAR, CODCAR)
R034FUN.(NUMEMP, CODCCU) = R018CCU.(NUMEMP, CODCCU)
```

### Regra homologada de elegibilidade

Consulta completa de `R010SIT`, executada em 2026-07-27 com o usuário administrativo `VETORH`, confirmou:

| `CODSIT` | `DESSIT` | Elegível no SGPD |
|---:|---|---|
| 1 | Trabalhando | Sim |
| 2 | Férias | Sim |
| 7 | Demitido | Não |

A regra funcional é:

```sql
R034FUN.SITAFA <> 7
```

Para o SGPD, “ativo/elegível” significa “não demitido”. Portanto, outros afastamentos cadastrados em `R010SIT` também permanecem elegíveis enquanto seu código for diferente de 7.

### Limites do contrato cadastral

- local de trabalho foi retirado do escopo e não será consultado nem usado nas regras do MVP;
- gestor não vem do Senior: será um usuário cadastrado no SGPD e selecionado na abertura do processo;
- e-mail não vem do Senior: será mantido no perfil do usuário do SGPD;
- nenhum usuário, gestor, e-mail, papel ou permissão do sistema será provisionado pelo Senior;
- a integração futura com AD vinculará identidades às contas SGPD existentes apenas para autenticação.

## 6. Padrão de implementação futura

O acesso deve usar `django.db.connection.cursor()` ou conexão Oracle dedicada homologada, encapsulada em um repository sem models:

```text
Django view / endpoint
    -> service de consulta
        -> repository Oracle read-only
            -> SELECT parametrizado em VETORH.*
```

Regras:

- bind variables para empresa, filial, tipo, matrícula e busca textual;
- filtros mínimos obrigatórios antes de listar colaboradores;
- paginação e limite de linhas;
- timeout configurado;
- aliases técnicos estáveis, sem depender de rótulos de apresentação;
- datas retornadas como datas, não como strings formatadas;
- `USU_DATALT` retornada como marcador anulável de atualização da origem;
- CPF mascarado por padrão e CPF completo somente no caso de uso autorizado;
- tratamento explícito de indisponibilidade;
- logs com correlation ID, sem SQL contendo valores pessoais;
- testes de contrato para colunas e grants;
- nenhuma tentativa de criar, alterar ou excluir objetos do Senior.

## 7. Snapshot

No início do processo:

1. executar novamente a consulta pela chave completa;
2. validar que existe exatamente um colaborador elegível;
3. validar permissão do usuário solicitante;
4. copiar os dados necessários para o snapshot do SGPD na mesma transação da abertura;
5. registrar data da consulta e identidade externa;
6. impedir atualização automática do snapshot.

O snapshot é persistência de domínio do SGPD. Ele não é cache nem réplica cadastral do Senior.

## 8. Segurança e segregação

- nunca usar o owner `VETORH` na aplicação;
- nunca usar o owner `SGPD` como usuário de runtime;
- conceder ao futuro usuário operacional `SELECT` apenas nos objetos homologados do Senior;
- conceder DML apenas nos objetos necessários do SGPD;
- manter credenciais fora do código;
- não registrar DSN, senha ou CPF completo;
- restringir o `.env` local a modo `600`;
- revisar periodicamente os grants.

## 9. Falhas

Como não existe réplica local, indisponibilidade do Senior impede novas pesquisas e a abertura de processos que dependam de um snapshot novo.

Nessa situação:

- processos e snapshots existentes continuam disponíveis;
- a aplicação informa indisponibilidade sem expor detalhes do Oracle;
- a falha é registrada com correlation ID;
- a consulta pode ser repetida com backoff limitado;
- não se usa dado cadastral antigo para abrir processo silenciosamente.

## 10. Pendências de descoberta

- confirmar versão exata do Senior HCM, distinta da versão do Oracle;
- homologar o contrato de acesso direto às tabelas internas;
- criar e validar o usuário operacional separado do owner;
- confirmar tratamento de `DATAFA = DATE '1900-12-31'`;
- decidir se `INNER JOIN` deve excluir colaboradores com referência incompleta;
- medir plano e tempo das consultas com filtros reais;
- definir timeout e limites de paginação;
- definir estratégia de homologação e monitoramento.
