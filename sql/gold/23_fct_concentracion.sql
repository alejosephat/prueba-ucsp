-- HECHO CONCENTRACION (componente estadistico, parte 2)
-- GRANULARIDAD: una fila por anio x universidad.
-- HHI (Herfindahl-Hirschman) = suma de los cuadrados de la participacion de
-- cada programa en la matricula de su universidad, escalado 0-10000.
--   ~10000 = toda la matricula en un solo programa
--   ~10000/n = matricula repartida en partes iguales entre n programas
-- Responde "distribucion de la matricula por programa" de la pregunta 4.1.
CREATE OR REPLACE TABLE fct_concentracion AS
-- Se calcula sobre la serie anual comparable (un solo semestre por anio). Sin
-- este filtro, ahora que estan cargados los 12 semestres, el HHI se calcularia
-- sobre la matricula de los dos semestres sumados: una persona matriculada en
-- los dos contaria doble y la concentracion saldria distorsionada.
-- El semestre no se escribe como literal: se toma de dim_semestre, que lo
-- hereda de ref_parametros y por tanto de config.py.
WITH por_programa AS (
    SELECT f.anio, f.codigo_inei, f.programa_sk, sum(f.matriculados) AS matriculados
    FROM fct_matricula f
    JOIN dim_semestre s ON s.semestre = f.semestre AND s.es_serie_anual
    GROUP BY 1, 2, 3
),
con_participacion AS (
    SELECT anio, codigo_inei, matriculados,
           matriculados * 1.0 / sum(matriculados) OVER (PARTITION BY anio, codigo_inei) AS share
    FROM por_programa
)
SELECT anio,
       codigo_inei,
       round(sum(share * share) * 10000, 1) AS hhi,
       count(*)                             AS programas,
       sum(matriculados)                    AS matriculados_universidad
FROM con_participacion
GROUP BY 1, 2;
