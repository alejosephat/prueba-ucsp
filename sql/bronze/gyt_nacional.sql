-- BRONZE -> SILVER: grados y titulos nacionales (titulacion efectiva).
--
-- Esta fuente NO comparte las llaves del modelo: trae CODIGO_ENTIDAD ('065'),
-- que no es el codigo INEI, y NOMBRE_CARRERA en texto libre en vez de
-- CODIGO_SIU_PROGRAMA. La unica llave viable es el nombre de la universidad
-- normalizado, y el control #11 mide que porcentaje de titulos resuelve asi.
-- Se carga a silver con ese nombre sin resolver; la decision de llevarlo o no
-- a gold depende de la tasa medida, no de un supuesto.
--
-- anios_estudio: FECHA_MATRICULA y FECHA_EGRESO vienen en dd/mm/yyyy (distinto
-- del resto de la fuente, que usa ISO) -> try_strptime, que devuelve NULL en vez
-- de fallar si alguna fila trae otro formato.

-- quote='' NO es opcional en esta fuente. GYT_Nacionales_2021.csv trae en la
-- columna PROGRAMA_ACREDITADO_SINEACE el valor
--     "SI" RP.NRO.000135-2020-SINEACE/CDAH-P
-- Son 2 filas de 327 475, pero el campo EMPIEZA por comilla: el parser la toma
-- como apertura de campo entrecomillado, no encuentra el cierre y aborta el
-- archivo completo. Los planos de TUNI no entrecomillan nada -- el separador es
-- el pipe y las comillas que aparecen son literales -- asi que declarar que no
-- hay caracter de cita describe el formato real. Se aplica a los siete
-- cargadores y no solo a este, porque la misma comilla en cualquier periodo
-- futuro romperia igual al que la reciba. Ver decision C4.
CREATE OR REPLACE TEMP VIEW crudo AS
SELECT * FROM read_csv('{ruta}', delim='|', header=true, encoding='cp1252',
                       all_varchar=true, ignore_errors=false, quote='');

INSERT INTO silver_conteo_crudo
SELECT 'gyt_nacional', '{periodo}', COUNT(*),
       COUNT(*) FILTER (WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}'))
FROM crudo;

INSERT INTO silver_titulo
SELECT
    TRY_CAST(ANIO_RESOLUCION AS SMALLINT),
    limpio(NOMBRE_ENTIDAD),
    limpio(TIPO_ENTIDAD),
    limpio(TIPO_GESTION),
    limpio(ESTADO_LICENCIAMIENTO),
    limpio(NIVEL_ACADEMICO),
    limpio(DEPARTAMENTO_SEDE_PRINCIPAL),
    limpio(NOMBRE_CARRERA),
    limpio(ABREVIATURA_GRADO_TITULO),
    limpio(MODALIDAD_OBTENCION_TITULO_GRADO),
    TRY_CAST(date_diff('day', try_strptime(FECHA_MATRICULA, '%d/%m/%Y'),
                              try_strptime(FECHA_EGRESO,    '%d/%m/%Y'))
             / 365.25 AS DECIMAL(5, 2)),
    limpio(IDENTIFICADOR_PERSONA),
    limpio(SEXO)
FROM crudo
WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}');
