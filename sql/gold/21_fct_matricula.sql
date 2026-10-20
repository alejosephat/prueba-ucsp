-- HECHO MATRICULA
-- GRANULARIDAD: una fila por anio x SEMESTRE x universidad x programa x ubicacion.
--
-- DECISION DE GRANO (revisada al ampliar la ingesta): la fuente publica la
-- matricula por semestre, y ahora estan cargados los 12 semestres de 2020-I a
-- 2025-II. Antes el hecho se anclaba al semestre I y los demas no se
-- descargaban; eso era un recorte de DATOS. Ahora el semestre es una dimension
-- del hecho: la serie anual comparable se obtiene filtrando
-- dim_semestre[es_serie_anual], que es un filtro de MEDIDA y no una perdida.
--
-- Lo que esto habilita y antes era imposible:
--   * retencion intra-anual: matricula del II sobre la del I del mismo anio
--   * el control #08 deja de estimar un sesgo con un solo anio (2025) y lo mide
--     en los seis
-- No hay doble conteo: el semestre forma parte del grano declarado, asi que
-- sumar los dos semestres de un anio es una operacion que el modelo permite
-- pero que ninguna medida hace por accidente.
CREATE OR REPLACE TABLE fct_matricula AS
SELECT m.anio,
       m.semestre,
       m.codigo_inei,
       md5(m.codigo_inei || '-' || m.codigo_siu_programa)              AS programa_sk,
       md5(norm(m.departamento) || '-' || coalesce(norm(m.provincia), '')) AS ubicacion_sk,
       count(DISTINCT m.guid_persona)                                   AS matriculados
FROM silver_matriculado m
WHERE m.codigo_inei IS NOT NULL
  AND m.codigo_siu_programa IS NOT NULL
  AND m.departamento IS NOT NULL
  AND m.semestre IS NOT NULL
GROUP BY 1, 2, 3, 4, 5;
