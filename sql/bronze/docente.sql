-- BRONZE -> SILVER: docentes. Grano del crudo: una fila por docente-periodo-grado
-- (la fuente repite al docente por cada grado o titulo que acredita), de ahi que
-- el hecho cuente personas distintas y no filas.
--
-- ESTA FUENTE NO TRAE PROGRAMA. Tampoco la ubicacion del local donde ensena:
-- DEPARTAMENTO_NACIMIENTO es donde nacio el docente, no donde trabaja, y usarlo
-- como geografia del hecho seria un error de interpretacion. Por eso el hecho
-- vive a grano universidad x semestre.
-- Nombres propios: ENTIDAD, PERIODO_ESTANDAR, LICENCIA.

CREATE OR REPLACE TEMP VIEW crudo AS
SELECT * FROM read_csv('{ruta}', delim='|', header=true, encoding='cp1252',
                       all_varchar=true, ignore_errors=false, quote='');

INSERT INTO silver_conteo_crudo
SELECT 'docente', '{periodo}', COUNT(*),
       COUNT(*) FILTER (WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}'))
FROM crudo;

INSERT INTO silver_docente
SELECT
    CAST(split_part(PERIODO_ESTANDAR, '-', 1) AS SMALLINT),
    CAST(split_part(PERIODO_ESTANDAR, '-', 2) AS TINYINT),
    limpio(CODIGO_INEI),
    limpio(ENTIDAD),
    limpio(TIPO_ENTIDAD),
    limpio(TIPO_GESTION),
    limpio(TIPO_CONSTITUCION),
    limpio(LICENCIA),
    limpio(NIVEL_ACADEMICO),
    limpio(GUID_PERSONA),
    limpio(TIPO_GRADO_TITULO),
    limpio(CONDICION_LABORAL),
    limpio(REGIMEN_DEDICACION),
    limpio(SEXO),
    TRY_CAST(EDAD AS SMALLINT)
FROM crudo
WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}');
