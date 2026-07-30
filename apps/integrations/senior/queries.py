"""Canonical runtime SQL for the read-only Senior HCM contract."""

LIST_COMPANIES = """
SELECT c.numemp AS empresa,
       MIN(c.razsoc) KEEP (DENSE_RANK FIRST ORDER BY c.codfil) AS razao_social
  FROM vetorh.r030fil c
 WHERE EXISTS (
           SELECT 1
             FROM vetorh.r034fun a
            WHERE a.numemp = c.numemp
              AND a.sitafa <> 7
       )
 GROUP BY c.numemp
 ORDER BY c.numemp
 OFFSET :offset ROWS FETCH NEXT :limite ROWS ONLY
"""

LIST_BRANCHES = """
SELECT c.numemp AS empresa,
       c.codfil AS filial,
       c.nomfil AS nome_filial
  FROM vetorh.r030fil c
 WHERE c.numemp = :empresa
   AND EXISTS (
           SELECT 1
             FROM vetorh.r034fun a
            WHERE a.numemp = c.numemp
              AND a.codfil = c.codfil
              AND a.sitafa <> 7
       )
 GROUP BY c.numemp, c.codfil, c.nomfil
 ORDER BY c.codfil
 OFFSET :offset ROWS FETCH NEXT :limite ROWS ONLY
"""

LIST_EMPLOYEE_TYPES = """
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
 OFFSET :offset ROWS FETCH NEXT :limite ROWS ONLY
"""

_EMPLOYEE_FIELDS = """
SELECT a.numemp AS empresa,
       a.codfil AS filial,
       c.nomfil AS nome_filial,
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
"""

LIST_EMPLOYEES = (
    _EMPLOYEE_FIELDS
    + """
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
 OFFSET :offset ROWS FETCH NEXT :limite ROWS ONLY
"""
)

GET_EMPLOYEE = """
SELECT a.numemp AS empresa,
       a.codfil AS filial,
       c.nomfil AS nome_filial,
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
   AND a.sitafa <> 7
"""

ALL_QUERIES = {
    "list_companies": LIST_COMPANIES,
    "list_branches": LIST_BRANCHES,
    "list_employee_types": LIST_EMPLOYEE_TYPES,
    "list_employees": LIST_EMPLOYEES,
    "get_employee": GET_EMPLOYEE,
}
