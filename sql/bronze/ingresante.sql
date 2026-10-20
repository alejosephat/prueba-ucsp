-- BRONZE -> SILVER: ingresantes. {ruta} y {periodo} los sustituye 02_transformar.py.
-- Grano del crudo: una fila por persona que ingresa.

CREATE OR REPLACE TEMP VIEW crudo AS
SELECT * FROM read_csv('{ruta}', delim='|', header=true, encoding='cp1252',
                       all_varchar=true, ignore_errors=false, quote='');

-- Conteo previo al filtro: insumo del control de calidad #1 (conciliacion).
INSERT INTO silver_conteo_crudo
SELECT 'ingresante', '{periodo}', COUNT(*),
       COUNT(*) FILTER (WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}'))
FROM crudo;

INSERT INTO silver_ingresante
SELECT
    CAST(PROCESO_ESTANDARIZADO AS SMALLINT),
    limpio(CODIGO_INEI),
    limpio(NOMBRE_ENTIDAD),
    limpio(TIPO_ENTIDAD),
    limpio(TIPO_GESTION),
    limpio(TIPO_CONSTITUCION),
    limpio(LICENCIADO),            -- en matriculado se llama LICENCIA
    limpio(NIVEL_ACADEMICO),
    limpio(CODIGO_SIU_PROGRAMA),
    limpio(CODIGO_GRUPO_1),
    limpio(NOMBRE_GRUPO_1),
    limpio(CODIGO_GRUPO_3),
    limpio(NOMBRE_GRUPO_3),
    limpio(NOMBRE_PROGRAMA),
    limpio(DEPARTAMENTO_FILIAL),   -- en matriculado es DEPARTAMENTO_LOCAL
    limpio(PROVINCIA_FILIAL),
    limpio(GUID_PERSONA),
    limpio(SEXO),
    TRY_CAST(EDAD AS SMALLINT)
FROM crudo
WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}');
