-- DIM UBICACION. Llave: hash(departamento, provincia) normalizados.
-- Grano departamento+provincia porque es la interseccion real entre fuentes:
-- ingresantes/postulantes traen la FILIAL y matriculados el LOCAL, que no son
-- el mismo codigo. Departamento y provincia si son comparables.
CREATE OR REPLACE TABLE dim_ubicacion AS
WITH todo AS (
    SELECT departamento, provincia FROM silver_ingresante
    UNION ALL SELECT departamento, provincia FROM silver_matriculado
    UNION ALL SELECT departamento, provincia FROM silver_postulante
),
agrupado AS (
    SELECT norm(departamento) AS dep_k,
           norm(provincia)    AS prov_k,
           max(departamento)  AS departamento,
           max(provincia)     AS provincia
    FROM todo
    WHERE departamento IS NOT NULL
    GROUP BY 1, 2
)
SELECT md5(a.dep_k || '-' || coalesce(a.prov_k, '')) AS ubicacion_sk,
       a.departamento,
       a.provincia,
       coalesce(m.macrorregion, 'Sin clasificar') AS macrorregion,
       coalesce(m.macrorregion, '') = 'Sur'       AS es_macrosur
FROM agrupado a
LEFT JOIN ref_macrorregion m ON m.departamento = a.dep_k;
