-- HECHO EGRESADOS
-- GRANULARIDAD: una fila por anio x semestre x universidad x programa.
--
-- OJO: ESTE HECHO NO SE RELACIONA CON dim_ubicacion, y no es un olvido.
-- Medido sobre los cuatro archivos de egresados: DEPARTAMENTO_FILIAL y
-- PROVINCIA_FILIAL vienen vacios en el 100 % de las 587 527 filas. La fuente
-- publica el local de egreso (LOCAL_EGRESO, por ejemplo F07L01) pero no su
-- geografia, y ese codigo no es el mismo que usa ningun otro dataset.
--
-- La alternativa era imputar el departamento de la sede principal de la
-- universidad. Se descarto: para una universidad de un solo local es correcto,
-- pero para las que tienen filiales en varios departamentos seria inventar
-- geografia. Se prefiere una relacion que falta y esta declarada, a un dato
-- que parece existir y es falso. Consecuencia practica, documentada tambien en
-- el catalogo de medidas: el slicer de departamento NO filtra los egresados.
--
-- Aporta dos medidas que ninguna otra fuente del portal tiene: nota promedio y
-- creditos aprobados al egresar.
CREATE OR REPLACE TABLE fct_egresados AS
SELECT e.anio,
       e.semestre,
       e.codigo_inei,
       md5(e.codigo_inei || '-' || e.codigo_siu_programa) AS programa_sk,
       count(DISTINCT e.guid_persona)                     AS egresados,
       round(avg(e.nota_promedio), 2)                     AS nota_promedio,
       round(avg(e.creditos_aprobados), 1)                AS creditos_aprobados
FROM silver_egresado e
WHERE e.codigo_inei IS NOT NULL
  AND e.codigo_siu_programa IS NOT NULL
  AND e.anio IS NOT NULL
GROUP BY 1, 2, 3, 4;
