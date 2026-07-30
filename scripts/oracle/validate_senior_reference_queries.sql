-- Validação read-only do contrato cadastral Senior.
-- Pré-condição: sessão já conectada como SGPD.
-- O script retorna somente contagens e metadados, sem dados pessoais.

WHENEVER OSERROR EXIT FAILURE
WHENEVER SQLERROR EXIT SQL.SQLCODE

SET FEEDBACK OFF
SET HEADING ON
SET SQLFORMAT CSV
SET TIMING ON

VARIABLE empresa NUMBER
VARIABLE filial NUMBER
VARIABLE tipo_colaborador NUMBER
VARIABLE matricula NUMBER
VARIABLE busca VARCHAR2(100)
VARIABLE offset_linhas NUMBER
VARIABLE limite_linhas NUMBER

BEGIN
    SELECT numemp, codfil, tipcol, numcad
      INTO :empresa, :filial, :tipo_colaborador, :matricula
      FROM (
          SELECT a.numemp, a.codfil, a.tipcol, a.numcad
            FROM vetorh.r034fun a
           WHERE a.sitafa <> 7
           ORDER BY a.numemp, a.codfil, a.tipcol, a.numcad
      )
     WHERE ROWNUM = 1;

    :busca := NULL;
    :offset_linhas := 0;
    :limite_linhas := 10;
END;
/

SELECT COUNT(*) AS empresas_probe
  FROM (
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
       OFFSET :offset_linhas ROWS
       FETCH NEXT :limite_linhas ROWS ONLY
  );

SELECT COUNT(*) AS filiais_probe
  FROM (
      SELECT c.numemp, c.codfil, c.nomfil
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
       OFFSET :offset_linhas ROWS
       FETCH NEXT :limite_linhas ROWS ONLY
  );

SELECT COUNT(*) AS tipos_probe
  FROM (
      SELECT a.tipcol
        FROM vetorh.r034fun a
       WHERE a.numemp = :empresa
         AND a.codfil = :filial
         AND a.sitafa <> 7
       GROUP BY a.tipcol
       ORDER BY a.tipcol
       OFFSET :offset_linhas ROWS
       FETCH NEXT :limite_linhas ROWS ONLY
  );

SELECT COUNT(*) AS colaboradores_probe
  FROM (
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
       OFFSET :offset_linhas ROWS
       FETCH NEXT :limite_linhas ROWS ONLY
  );

SELECT COUNT(*) AS colaborador_detalhe_probe
  FROM (
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
  );

SELECT base.quantidade AS colaboradores_base,
       joined.quantidade AS colaboradores_com_relacoes,
       base.quantidade - joined.quantidade AS excluidos_por_inner_join
  FROM (
      SELECT COUNT(*) AS quantidade
        FROM vetorh.r034fun a
       WHERE a.numemp = :empresa
         AND a.codfil = :filial
         AND a.tipcol = :tipo_colaborador
         AND a.sitafa <> 7
  ) base
  CROSS JOIN (
      SELECT COUNT(*) AS quantidade
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
  ) joined;

SELECT COUNT(*) AS elegiveis,
       SUM(
           CASE
               WHEN NOT EXISTS (
                   SELECT 1
                     FROM vetorh.r010sit b
                    WHERE b.codsit = a.sitafa
               )
               THEN 1 ELSE 0
           END
       ) AS sem_situacao,
       SUM(
           CASE
               WHEN NOT EXISTS (
                   SELECT 1
                     FROM vetorh.r030fil c
                    WHERE c.numemp = a.numemp
                      AND c.codfil = a.codfil
               )
               THEN 1 ELSE 0
           END
       ) AS sem_filial,
       SUM(
           CASE
               WHEN NOT EXISTS (
                   SELECT 1
                     FROM vetorh.r024car d
                    WHERE d.estcar = a.estcar
                      AND d.codcar = a.codcar
               )
               THEN 1 ELSE 0
           END
       ) AS sem_cargo,
       SUM(
           CASE
               WHEN NOT EXISTS (
                   SELECT 1
                     FROM vetorh.r018ccu e
                    WHERE e.numemp = a.numemp
                      AND e.codccu = a.codccu
               )
               THEN 1 ELSE 0
           END
       ) AS sem_centro_custo
  FROM vetorh.r034fun a
 WHERE a.sitafa <> 7;

SELECT base.quantidade AS colaboradores_base,
       joined_left.quantidade AS colaboradores_com_left_join,
       joined_inner.quantidade AS colaboradores_com_inner_join_centro_custo,
       base.quantidade - joined_inner.quantidade AS preservados_pelo_left_join
  FROM (
      SELECT COUNT(*) AS quantidade
        FROM vetorh.r034fun a
       WHERE a.sitafa <> 7
  ) base
  CROSS JOIN (
      SELECT COUNT(*) AS quantidade
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
       WHERE a.sitafa <> 7
  ) joined_left
  CROSS JOIN (
      SELECT COUNT(*) AS quantidade
        FROM vetorh.r034fun a
        INNER JOIN vetorh.r010sit b
                ON b.codsit = a.sitafa
        INNER JOIN vetorh.r030fil c
                ON c.numemp = a.numemp
               AND c.codfil = a.codfil
        INNER JOIN vetorh.r024car d
                ON d.estcar = a.estcar
               AND d.codcar = a.codcar
        INNER JOIN vetorh.r018ccu e
                ON e.numemp = a.numemp
               AND e.codccu = a.codccu
       WHERE a.sitafa <> 7
  ) joined_inner;

SELECT COUNT(*) AS chaves_centro_custo_duplicadas
  FROM (
      SELECT e.numemp, e.codccu
        FROM vetorh.r018ccu e
       GROUP BY e.numemp, e.codccu
      HAVING COUNT(*) > 1
  );

SELECT column_name, data_type, nullable
  FROM all_tab_columns
 WHERE owner = 'VETORH'
   AND table_name = 'R034FUN'
   AND column_name = 'USU_DATALT';

SELECT COUNT(*) AS elegiveis,
       SUM(CASE WHEN datafa IS NULL THEN 1 ELSE 0 END) AS datafa_nula,
       SUM(CASE WHEN datafa = DATE '1900-12-31' THEN 1 ELSE 0 END) AS datafa_sentinela
  FROM vetorh.r034fun
 WHERE sitafa <> 7;

EXIT SUCCESS
