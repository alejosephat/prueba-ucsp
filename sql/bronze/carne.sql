-- BRONZE -> SILVER: carnes universitarios emitidos.
-- NO es un hecho del modelo: cuenta tramites administrativos, no alumnos.
-- Se ingesta para contrastar la matricula contra una fuente independiente
-- (control de calidad #10).
-- OJO CON LA COLUMNA GUID: no identifica personas. Medido: 405 488 filas de
-- 2021 tienen solo 321 valores distintos, cada uno asociado a UNA universidad
-- pero a decenas de programas y departamentos, con conteos redondos (12 000,
-- 20 000). Es un identificador de LOTE de emision, no de persona. Se carga tal
-- cual porque es lo que la fuente publica, pero NINGUNA medida hace
-- count(DISTINCT guid_persona) sobre esta tabla: el control #15 lo demuestra y
-- el #12 cuenta filas. Es la razon ultima por la que los carnes no son un hecho:
-- una fuente que no permite contar personas no puede medir matricula.
-- Geografia: UBICACION viene como 'DEPARTAMENTO/PROVINCIA/DISTRITO'.
-- NIVEL_ACADEMICO viene en MAYUSCULAS aqui y en Mixto en las demas fuentes:
-- por eso el filtro compara norm(...) = norm(...) y no los literales.

CREATE OR REPLACE TEMP VIEW crudo AS
SELECT * FROM read_csv('{ruta}', delim='|', header=true, encoding='cp1252',
                       all_varchar=true, ignore_errors=false, quote='');

INSERT INTO silver_conteo_crudo
SELECT 'carne', '{periodo}', COUNT(*),
       COUNT(*) FILTER (WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}'))
FROM crudo;

INSERT INTO silver_carne
SELECT
    TRY_CAST(ANIO_EMISION AS SMALLINT),
    limpio(CODIGO_INEI),
    limpio(NOMBRE_ENTIDAD),
    limpio(NIVEL_ACADEMICO),
    limpio(CODIGO_SIU_PROGRAMA),
    limpio(NOMBRE_PROGRAMA),
    limpio(split_part(UBICACION, '/', 1)),
    limpio(split_part(UBICACION, '/', 2)),
    limpio(GUID)
FROM crudo
WHERE norm(NIVEL_ACADEMICO) = norm('{nivel}');
