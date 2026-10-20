-- HECHO INGRESANTES
-- GRANULARIDAD: una fila por anio x universidad x programa x ubicacion.
-- Medida: ingresantes = personas distintas que ingresan (COUNT DISTINCT sobre
-- guid_persona, por si la fuente repite a una persona en el mismo programa).
CREATE OR REPLACE TABLE fct_ingresantes AS
SELECT i.anio,
       i.codigo_inei,
       md5(i.codigo_inei || '-' || i.codigo_siu_programa)              AS programa_sk,
       md5(norm(i.departamento) || '-' || coalesce(norm(i.provincia), '')) AS ubicacion_sk,
       count(DISTINCT i.guid_persona)                                   AS ingresantes
FROM silver_ingresante i
WHERE i.codigo_inei IS NOT NULL
  AND i.codigo_siu_programa IS NOT NULL
  AND i.departamento IS NOT NULL
GROUP BY 1, 2, 3, 4;
