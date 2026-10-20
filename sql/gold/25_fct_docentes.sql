-- HECHO DOCENTES
-- GRANULARIDAD: una fila por anio x semestre x universidad.
--
-- GRANO MAS GRUESO QUE LOS DEMAS HECHOS, Y DECLARADO: la fuente de docentes no
-- trae CODIGO_SIU_PROGRAMA, asi que no se puede saber en que programa ensena
-- cada docente. Tampoco trae la ubicacion del local donde trabaja (su unica
-- geografia es DEPARTAMENTO_NACIMIENTO, que es otra cosa). Este hecho se
-- relaciona entonces con dim_universidad, dim_periodo y dim_semestre, y NO con
-- dim_programa ni dim_ubicacion.
--
-- En un esquema estrella eso es legitimo: un hecho se relaciona con las
-- dimensiones de su propio grano. Lo que NO seria legitimo es repartir los
-- docentes entre los programas de su universidad para forzar el cruce; eso
-- fabricaria un dato que la fuente no publica.
--
-- La fuente repite al docente una vez por cada grado o titulo que acredita, de
-- ahi el COUNT DISTINCT sobre la persona y no un COUNT de filas.
--
-- POR QUE ESTA FUENTE SI APORTA: el ratio alumno/docente y el porcentaje de
-- docentes a tiempo completo son Condiciones Basicas de Calidad del
-- licenciamiento SUNEDU. Son los indicadores con los que la propia reguladora
-- mide a las universidades, asi que convierten el benchmark de la 4.1 de
-- cuantos alumnos tiene cada una, a con que capacidad docente los atiende.
CREATE OR REPLACE TABLE fct_docentes AS
SELECT d.anio,
       d.semestre,
       d.codigo_inei,
       count(DISTINCT d.guid_persona)                                   AS docentes,
       count(DISTINCT d.guid_persona) FILTER (
           WHERE norm(d.regimen_dedicacion) IN ('TIEMPO COMPLETO', 'DEDICACION EXCLUSIVA')
       )                                                                AS docentes_tiempo_completo,
       count(DISTINCT d.guid_persona) FILTER (
           WHERE norm(d.tipo_grado_titulo) IN ('MAESTRO', 'DOCTOR')
       )                                                                AS docentes_posgrado,
       count(DISTINCT d.guid_persona) FILTER (
           WHERE norm(d.condicion_laboral) = 'ORDINARIO'
       )                                                                AS docentes_ordinarios
FROM silver_docente d
WHERE d.codigo_inei IS NOT NULL
  AND d.anio IS NOT NULL
  AND d.semestre IS NOT NULL
GROUP BY 1, 2, 3;
