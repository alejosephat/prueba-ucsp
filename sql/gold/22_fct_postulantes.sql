-- HECHO POSTULANTES (fuente adicional, pregunta 4.4)
-- GRANULARIDAD: una fila por anio x universidad x programa (1a opcion) x ubicacion.
--
-- Tres medidas porque responden preguntas distintas:
--   postulaciones = COUNT(*)            -> volumen de demanda recibida
--   postulantes   = personas distintas  -> demanda sin inflar por multipostulacion
--   admitidos     = ES_INGRESANTE = SI  -> viene en la propia fuente, asi que la
--                   selectividad se calcula dentro de la tabla, sin cruzar datasets
CREATE OR REPLACE TABLE fct_postulantes AS
SELECT p.anio,
       p.codigo_inei,
       md5(p.codigo_inei || '-' || p.codigo_siu_programa)              AS programa_sk,
       md5(norm(p.departamento) || '-' || coalesce(norm(p.provincia), '')) AS ubicacion_sk,
       count(*)                                     AS postulaciones,
       count(DISTINCT p.guid_persona)               AS postulantes,
       count(*) FILTER (WHERE p.es_ingresante)      AS admitidos
FROM silver_postulante p
WHERE p.codigo_inei IS NOT NULL
  AND p.codigo_siu_programa IS NOT NULL
  AND p.departamento IS NOT NULL
GROUP BY 1, 2, 3, 4;
