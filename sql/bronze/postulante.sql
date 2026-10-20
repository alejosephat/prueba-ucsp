-- BRONZE -> SILVER: postulantes (fuente adicional, pregunta 4.4).
-- Se toma la PRIMERA OPCION de programa. Ojo con los nombres de columna del
-- crudo: los de grupo vienen truncados como *_PRIMERA_O, no *_PRIMERA_OPCION.

CREATE OR REPLACE TEMP VIEW crudo AS
SELECT * FROM read_csv('{ruta}', delim='|', header=true, encoding='cp1252',
                       all_varchar=true, ignore_errors=false, quote='');

INSERT INTO silver_conteo_crudo
SELECT 'postulante', '{periodo}', COUNT(*),
       COUNT(*) FILTER (WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}'))
FROM crudo;

INSERT INTO silver_postulante
SELECT
    CAST(PROCESO_ESTANDARIZADO AS SMALLINT),
    limpio(CODIGO_INEI),
    limpio(NOMBRE_ENTIDAD),
    limpio(TIPO_ENTIDAD),
    limpio(TIPO_GESTION),
    limpio(TIPO_CONSTITUCION),
    limpio(LICENCIADO),
    limpio(NIVEL_ACADEMICO),
    limpio(MODALIDAD_INGRESO_GRUPO),
    limpio(CODIGO_SIU_PROGRAMA_PRIMERA_OPCION),
    limpio(CODIGO_GRUPO_1_PRIMERA_OPCION),
    limpio(NOMBRE_GRUPO_1_PRIMERA_O),
    limpio(CODIGO_GRUPO_3_PRIMERA_OPCION),
    limpio(NOMBRE_GRUPO_3_PRIMERA_O),
    limpio(NOMBRE_PROGRAMA_PRIMERA_OPCION),
    limpio(DEPARTAMENTO_FILIAL),
    limpio(PROVINCIA_FILIAL),
    limpio(GUID_PERSONA),
    limpio(SEXO),
    TRY_CAST(EDAD AS SMALLINT),
    norm(ES_INGRESANTE) = 'SI'
FROM crudo
WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}')
  AND limpio(CODIGO_SIU_PROGRAMA_PRIMERA_OPCION) IS NOT NULL;
