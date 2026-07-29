# Integração Senior HCM e Oracle

## 1. Objetivo

Consultar dados cadastrais do Senior HCM diretamente no Oracle, em tempo real e somente por `SELECT`, sem escrever nos objetos do Senior e sem replicar referências em models ou tabelas `REF_*` do SGPD.

## 2. Decisão de acesso

- o Senior HCM permanece como fonte oficial;
- a conexão Oracle do SGPD acessa objetos `VETORH` no mesmo serviço;
- os nomes dos objetos são qualificados pelo schema;
- o acesso ocorre por SQL parametrizado em um repository chamado pelos
  endpoints da API;
- não serão criados models Django, inclusive `managed = False`, para objetos do Senior;
- não serão criadas views Oracle locais nesta etapa;
- nenhum dado consultado é persistido até a abertura do processo;
- na abertura, o SGPD cria seu próprio snapshot histórico e auditável.

## 3. Ambiente validado em 2026-07-27

- Oracle Database 19c Enterprise Edition, versão 19.15.0.0.0;
- Oracle Instant Client 19.28;
- SQLcl local 26.1;
- serviço configurado no `.env` acessível;
- sessão do owner do SGPD confirmada como `SGPD`;
- schema de origem confirmado como `VETORH`;
- a conexão separada configurada com o owner `VETORH` funciona, mas é administrativa e não deve ser usada pela aplicação.

O `.env` real usa o owner `SGPD`. Por decisão explícita para o DEV, essa será a conexão única de runtime e migrations; não será criado `SGPD_APP`. O risco e os controles compensatórios estão registrados na ADR-022.

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

## 5. Contrato homologado da consulta

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

`R034FUN.DATAFA` será retornada como `NULL` quando estiver nula ou contiver a
sentinela `DATE '1900-12-31'`. Nos demais casos, continuará sendo retornada
como `DATE`, sem formatação textual no SQL. Na validação de 2026-07-28, entre
os 1.891 elegíveis, 1.818 usam a sentinela e 73 possuem outra data.

### Relações validadas

```text
R034FUN.SITAFA = R010SIT.CODSIT
R034FUN.(NUMEMP, CODFIL) = R030FIL.(NUMEMP, CODFIL)
R034FUN.(ESTCAR, CODCAR) = R024CAR.(ESTCAR, CODCAR)
R034FUN.(NUMEMP, CODCCU) = R018CCU.(NUMEMP, CODCCU)
```

Na validação global repetida em 2026-07-28 para os 1.891 colaboradores com
`SITAFA <> 7`:

- situação sem referência: 0;
- filial sem referência: 0;
- cargo sem referência: 0;
- centro de custo sem referência: 49.

O `LEFT JOIN` retornou os 1.891 colaboradores, enquanto o mesmo contrato com
`INNER JOIN` em `R018CCU` retornaria 1.842 e excluiria exatamente os 49 sem
referência. Não foram encontradas chaves duplicadas por `NUMEMP + CODCCU` em
`R018CCU`. O uso do `LEFT JOIN` está homologado para preservar o colaborador
quando a descrição do centro de custo estiver ausente. Os demais
relacionamentos permanecem `INNER JOIN` com base na integridade observada.

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
- nenhum usuário, gestor, e-mail, papel funcional, associação ou permissão do
  sistema será provisionado pelo Senior;
- a integração AD é independente do Senior: vincula ou cria explicitamente a
  conta SGPD a partir da identidade corporativa, sem importar papéis,
  associações ou permissões e sem usar dados Senior para autenticação.

## 6. Implementação

O acesso está implementado em `apps/integrations/senior/`, encapsulado em um
repository sem models:

```text
Endpoint da API
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

O repository:

- retorna dataclasses imutáveis, não models Django;
- valida inteiros, busca, offset e limite antes de abrir o cursor;
- aplica `oracledb.Connection.call_timeout` por consulta e restaura o valor
  anterior;
- converte erros de banco em erro de integração sem detalhes sensíveis;
- rejeita colunas ausentes e duplicidade da chave do colaborador como quebra
  de contrato;
- registra nome lógico da consulta, duração e quantidade de linhas, sem
  parâmetros, SQL ou dados pessoais.

### Endpoints da cascata

Os quatro endpoints `GET /api/v1/references/` estão implementados com
autenticação, permissão `query_senior_references` e escopo organizacional
obrigatórios:

- `companies/`;
- `branches/?company=`;
- `employee-types/?company=&branch=`;
- `employees/?company=&branch=&employee_type=&q=`.

As respostas incluem `offset`, `limit` e `results`, sem executar contagem
global. Empresas são filtradas pelo escopo; empresa ou filial não autorizada
retorna `403`. Parâmetros inválidos retornam `400`, indisponibilidade retorna
`503` e quebra do contrato de origem retorna `502`. Detalhes do driver e do
Oracle não são devolvidos ao cliente. A listagem de colaboradores não contém
CPF, nem mesmo mascarado.

### Interface da cascata

A seleção da SPA está disponível em `/fe/colaboradores` e consome os quatro
endpoints JSON homologados. O contrato de comportamento é:

- exige autenticação e reutiliza `query_senior_references` com o mesmo escopo
  de empresa/filial dos endpoints JSON;
- filtra empresas antes de exibir opções;
- limpa todos os níveis descendentes quando uma seleção anterior muda ou é
  removida;
- permite buscar colaborador por nome ou matrícula, com no máximo 100
  caracteres e 20 resultados por chamada;
- não projeta nem exibe CPF;
- preserva erros `400`, `403`, `502` e `503` sem expor detalhes do driver;
- não persiste referências e não cria snapshot.

Na SPA, as respostas assíncronas obsoletas são canceladas quando o usuário
troca um nível da cascata. A busca remota usa o filtro do `p-select`, aplica
debounce de 400 ms e mantém o limite de 20 resultados. A seleção final exibe
somente os campos já autorizados pelo endpoint.

A SPA não carrega código de CDN nem acessa rede externa para obter seus assets.

### Contrato SQL versionado

As consultas parametrizadas estão em [`sql/senior_reference_queries.sql`](sql/senior_reference_queries.sql):

- `listar_empresas`;
- `listar_filiais`;
- `listar_tipos_colaborador`;
- `listar_colaboradores`;
- `obter_colaborador`.

Limites iniciais:

- `offset` mínimo: 0;
- empresas, filiais e tipos: limite máximo de 100;
- colaboradores: limite padrão de 20 e máximo de 100;
- timeout inicial por chamada Oracle: 5 segundos.

O script `scripts/oracle/validate_senior_reference_queries.sql` valida binds, paginação, projeções, detalhe, integridade dos joins e `USU_DATALT`, retornando somente contagens e metadados.

Execução local a partir da raiz:

```bash
scripts/oracle/run_senior_contract_validation.sh
```

O wrapper lê a conexão `SGPD` do `.env` sem exibir credenciais.

No DEV, a cascata real executada pelo repository e pelos quatro endpoints
autenticados retornou uma linha em cada etapa e status `200`. As consultas
levaram entre 0,70 ms e 39,46 ms com conexão persistente.
O payload da listagem foi inspecionado por nomes de campos e não expôs CPF. O
detalhe interno confirmou `USU_DATALT` como `datetime` e CPF mascarado.

### Medição de concorrência em 2026-07-28

O script `scripts/oracle/benchmark_senior_concurrency.py` executou 80 consultas
somente leitura de listagem de colaboradores, usando uma conexão persistente
por worker e limite de 20 linhas:

| Conexões concorrentes | Consultas | Erros | p50 | p95 | Máximo |
|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 0 | 0,89 ms | 34,78 ms | 34,78 ms |
| 5 | 25 | 0 | 1,63 ms | 37,78 ms | 44,42 ms |
| 10 | 50 | 0 | 1,85 ms | 60,64 ms | 65,61 ms |

A execução limitada não apresentou erro nem timeout. O resultado homologa o
contrato para a carga DEV medida; não constitui dimensionamento de produção.

Execução:

```bash
uv run python scripts/oracle/benchmark_senior_concurrency.py
```

## 7. Snapshot

Na abertura do processo, implementada na Fase 4:

1. validar `DP` no escopo antes de consultar dados pessoais;
2. executar novamente `obter_colaborador` pela chave completa;
3. validar que existe exatamente um colaborador elegível e que a chave
   retornada é idêntica à solicitada;
4. iniciar a transação SGPD, bloquear ator, gestor e atribuições `DP` e repetir
   `has_effective_role()`;
5. impedir duplicidade de processo não encerrado pela identidade externa;
6. copiar os dados necessários para o snapshot na mesma transação da abertura;
7. registrar instante da consulta, identidade externa e `PROCESS_OPENED`;
8. impedir atualização ou exclusão do snapshot.

O snapshot é persistência de domínio do SGPD. Ele não é cache nem réplica cadastral do Senior.
O CPF mascarado permanece somente na tabela de snapshot e não é devolvido pelo
endpoint de abertura.

## 8. Segurança e segregação

- nunca usar o owner `VETORH` na aplicação;
- usar `SGPD` como conexão única do runtime DEV;
- manter os `SELECT` de `SGPD` limitados aos objetos homologados do Senior;
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

## 10. Pendência operacional

- definir estratégia de homologação e monitoramento.
