-- SGPD / DesligaFlow
-- Contrato de consultas cadastrais do Senior HCM.
--
-- Premissas:
--   * conexão: owner SGPD no ambiente DEV;
--   * acesso ao Senior: somente SELECT em objetos VETORH homologados;
--   * execução pela aplicação: cursor Oracle com bind variables;
--   * nenhuma tabela ou model REF_*;
--   * :offset >= 0 e 1 <= :limite <= limite máximo definido pela aplicação.
--
-- Este arquivo contém consultas independentes. Ele não deve ser executado
-- integralmente como um único script.

-- name: listar_empresas
-- binds: :offset NUMBER, :limite NUMBER
SELECT c.numemp AS empresa
  FROM vetorh.r030fil c
 WHERE EXISTS (
           SELECT 1
             FROM vetorh.r034fun a
            WHERE a.numemp = c.numemp
              AND a.sitafa <> 7
       )
 GROUP BY c.numemp
 ORDER BY c.numemp
 OFFSET :offset ROWS FETCH NEXT :limite ROWS ONLY;

-- name: listar_filiais
-- binds: :empresa NUMBER, :offset NUMBER, :limite NUMBER
SELECT c.numemp AS empresa,
       c.codfil AS filial,
       c.razsoc AS razao_social
  FROM vetorh.r030fil c
 WHERE c.numemp = :empresa
   AND EXISTS (
           SELECT 1
             FROM vetorh.r034fun a
            WHERE a.numemp = c.numemp
              AND a.codfil = c.codfil
              AND a.sitafa <> 7
       )
 GROUP BY c.numemp, c.codfil, c.razsoc
 ORDER BY c.codfil
 OFFSET :offset ROWS FETCH NEXT :limite ROWS ONLY;

-- name: listar_tipos_colaborador
-- binds: :empresa NUMBER, :filial NUMBER, :offset NUMBER, :limite NUMBER
SELECT a.tipcol AS tipo_colaborador,
       CASE a.tipcol
           WHEN 1 THEN 'Empregado'
           WHEN 2 THEN 'Terceiro'
           WHEN 3 THEN 'Parceiro'
           ELSE 'Desconhecido'
       END AS descricao_tipo_colaborador
  FROM vetorh.r034fun a
 WHERE a.numemp = :empresa
   AND a.codfil = :filial
   AND a.sitafa <> 7
 GROUP BY a.tipcol
 ORDER BY a.tipcol
 OFFSET :offset ROWS FETCH NEXT :limite ROWS ONLY;

-- name: listar_colaboradores
-- binds:
--   :empresa NUMBER, :filial NUMBER, :tipo_colaborador NUMBER,
--   :busca VARCHAR2 (anulável), :offset NUMBER, :limite NUMBER
-- Segurança: CPF não faz parte da listagem.
-- Integridade: R018CCU usa LEFT JOIN porque a validação encontrou
-- colaboradores elegíveis sem referência de centro de custo.
SELECT a.numemp AS empresa,
       a.codfil AS filial,
       c.razsoc AS razao_social,
       a.tipcol AS tipo_colaborador,
       CASE a.tipcol
           WHEN 1 THEN 'Empregado'
           WHEN 2 THEN 'Terceiro'
           WHEN 3 THEN 'Parceiro'
           ELSE 'Desconhecido'
       END AS descricao_tipo_colaborador,
       a.numcad AS matricula,
       a.nomfun AS funcionario,
       a.datadm AS data_admissao,
       a.sitafa AS codigo_afastamento,
       b.dessit AS descricao_afastamento,
       CASE
           WHEN a.datafa IS NULL
             OR a.datafa = DATE '1900-12-31'
           THEN CAST(NULL AS DATE)
           ELSE a.datafa
       END AS data_afastamento,
       a.estcar AS estrutura_cargos,
       a.codcar AS codigo_cargo,
       d.titcar AS descricao_cargo,
       a.codccu AS centro_custo,
       e.nomccu AS descricao_centro_custo,
       a.usu_datalt AS origem_atualizada_em
  FROM vetorh.r034fun a
  INNER JOIN vetorh.r010sit b
          ON b.codsit = a.sitafa
  INNER JOIN vetorh.r030fil c
          ON c.numemp = a.numemp
         AND c.codfil = a.codfil
  INNER JOIN vetorh.r024car d
          ON d.estcar = a.estcar
         AND d.codcar = a.codcar
  LEFT JOIN vetorh.r018ccu e
         ON e.numemp = a.numemp
        AND e.codccu = a.codccu
 WHERE a.numemp = :empresa
   AND a.codfil = :filial
   AND a.tipcol = :tipo_colaborador
   AND a.sitafa <> 7
   AND (
       :busca IS NULL
       OR INSTR(UPPER(a.nomfun), UPPER(:busca)) > 0
       OR TO_CHAR(a.numcad) = TRIM(:busca)
   )
 ORDER BY a.numcad
 OFFSET :offset ROWS FETCH NEXT :limite ROWS ONLY;

-- name: obter_colaborador
-- binds:
--   :empresa NUMBER, :filial NUMBER, :tipo_colaborador NUMBER,
--   :matricula NUMBER
-- Uso: releitura autorizada na abertura e criação do snapshot.
SELECT a.numemp AS empresa,
       a.codfil AS filial,
       c.razsoc AS razao_social,
       a.tipcol AS tipo_colaborador,
       CASE a.tipcol
           WHEN 1 THEN 'Empregado'
           WHEN 2 THEN 'Terceiro'
           WHEN 3 THEN 'Parceiro'
           ELSE 'Desconhecido'
       END AS descricao_tipo_colaborador,
       a.numcad AS matricula,
       a.nomfun AS funcionario,
       CASE
           WHEN a.numcpf IS NULL THEN NULL
           ELSE '***.***.***-' || SUBSTR(LPAD(TO_CHAR(a.numcpf), 11, '0'), 10, 2)
       END AS cpf_mascarado,
       a.datadm AS data_admissao,
       a.sitafa AS codigo_afastamento,
       b.dessit AS descricao_afastamento,
       CASE
           WHEN a.datafa IS NULL
             OR a.datafa = DATE '1900-12-31'
           THEN CAST(NULL AS DATE)
           ELSE a.datafa
       END AS data_afastamento,
       a.estcar AS estrutura_cargos,
       a.codcar AS codigo_cargo,
       d.titcar AS descricao_cargo,
       a.codccu AS centro_custo,
       e.nomccu AS descricao_centro_custo,
       a.usu_datalt AS origem_atualizada_em
  FROM vetorh.r034fun a
  INNER JOIN vetorh.r010sit b
          ON b.codsit = a.sitafa
  INNER JOIN vetorh.r030fil c
          ON c.numemp = a.numemp
         AND c.codfil = a.codfil
  INNER JOIN vetorh.r024car d
          ON d.estcar = a.estcar
         AND d.codcar = a.codcar
  LEFT JOIN vetorh.r018ccu e
         ON e.numemp = a.numemp
        AND e.codccu = a.codccu
 WHERE a.numemp = :empresa
   AND a.codfil = :filial
   AND a.tipcol = :tipo_colaborador
   AND a.numcad = :matricula
   AND a.sitafa <> 7;
