-- BRONZE -> SILVER: egresados. Grano del crudo: una fila por persona que egresa.
-- Integra con las dos llaves del modelo (codigo_inei, codigo_siu_programa).
-- PERIODO_EGRESO viene como '2025-1'; ANIO es el respaldo si viniera vacio.
-- Nombres propios de esta fuente: IDENTIFICADOR_PERSONA (no GUID_PERSONA),
-- LICENCIADO (no LICENCIA), DEPARTAMENTO_FILIAL (como ingresante).

CREATE OR REPLACE TEMP VIEW crudo AS
SELECT * FROM read_csv('{ruta}', delim='|', header=true, encoding='cp1252',
                       all_varchar=true, ignore_errors=false, quote='');

INSERT INTO silver_conteo_crudo
SELECT 'egresado', '{periodo}', COUNT(*),
       COUNT(*) FILTER (WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}'))
FROM crudo;

INSERT INTO silver_egresado
SELECT
    coalesce(TRY_CAST(split_part(PERIODO_EGRESO, '-', 1) AS SMALLINT),
             TRY_CAST(ANIO AS SMALLINT)),
    -- Medido: PERIODO_EGRESO trae 1, 2, y tambien 3 y 4 (0,43 %) mas 0,78 %
    -- vacio. Todo lo que no es semestre regular se manda a 0 = 'Otro' en
    -- dim_semestre; asi ninguna fila queda sin pareja al relacionar.
    CASE WHEN TRY_CAST(split_part(PERIODO_EGRESO, '-', 2) AS TINYINT) IN (1, 2)
         THEN TRY_CAST(split_part(PERIODO_EGRESO, '-', 2) AS TINYINT)
         ELSE 0 END,
    limpio(CODIGO_INEI),
    limpio(NOMBRE_ENTIDAD),
    limpio(TIPO_ENTIDAD),
    limpio(TIPO_GESTION),
    limpio(TIPO_CONSTITUCION),
    limpio(LICENCIADO),
    limpio(NIVEL_ACADEMICO),
    limpio(CODIGO_SIU_PROGRAMA),
    limpio(CODIGO_GRUPO_1),
    limpio(NOMBRE_GRUPO_1),
    limpio(CODIGO_GRUPO_3),
    limpio(NOMBRE_GRUPO_3),
    limpio(NOMBRE_PROGRAMA),
    limpio(DEPARTAMENTO_FILIAL),
    limpio(PROVINCIA_FILIAL),
    limpio(IDENTIFICADOR_PERSONA),
    limpio(SEXO),
    TRY_CAST(EDAD AS SMALLINT),
    TRY_CAST(CREDITOS_APROBADOS AS DECIMAL(8, 3)),
    TRY_CAST(NOTA_PROMEDIO AS DECIMAL(5, 2))
FROM crudo
WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}');
