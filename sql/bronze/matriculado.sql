-- BRONZE -> SILVER: matriculados. Grano del crudo: una fila por persona-periodo.
-- PERIODO_ESTANDARIZADO viene como '2025-2' -> se parte en anio y semestre.

CREATE OR REPLACE TEMP VIEW crudo AS
SELECT * FROM read_csv('{ruta}', delim='|', header=true, encoding='cp1252',
                       all_varchar=true, ignore_errors=false, quote='');

INSERT INTO silver_conteo_crudo
SELECT 'matriculado', '{periodo}', COUNT(*),
       COUNT(*) FILTER (WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}'))
FROM crudo;

INSERT INTO silver_matriculado
SELECT
    CAST(split_part(PERIODO_ESTANDARIZADO, '-', 1) AS SMALLINT),
    CAST(split_part(PERIODO_ESTANDARIZADO, '-', 2) AS TINYINT),
    limpio(CODIGO_INEI),
    limpio(NOMBRE_ENTIDAD),
    limpio(TIPO_ENTIDAD),
    limpio(TIPO_GESTION),
    limpio(TIPO_CONSTITUCION),
    limpio(LICENCIA),              -- en ingresante se llama LICENCIADO
    limpio(NIVEL_ACADEMICO),
    limpio(CODIGO_SIU_PROGRAMA),
    limpio(CODIGO_GRUPO_1),
    limpio(NOMBRE_GRUPO_1),
    limpio(CODIGO_GRUPO_3),
    limpio(NOMBRE_GRUPO_3),
    limpio(NOMBRE_PROGRAMA),
    limpio(DEPARTAMENTO_LOCAL),    -- en ingresante es DEPARTAMENTO_FILIAL
    limpio(PROVINCIA_LOCAL),
    limpio(GUID_PERSONA),
    limpio(SEXO),
    TRY_CAST(EDAD AS SMALLINT),
    TRY_CAST(ANIO_PERIODO_INGRESO AS SMALLINT)
FROM crudo
WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}');
