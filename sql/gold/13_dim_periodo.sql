-- DIM PERIODO. Grano: anio. Dimension conformada: se relaciona directamente
-- con los SEIS hechos, lo que permite filtrar ingresantes, matricula,
-- postulantes, egresados, docentes y titulos con un unico slicer.
--
-- El grano es ANUAL porque es el grano comun a todos los hechos: tres son
-- anuales en la fuente y tres son semestrales. El eje semestral vive en
-- dim_semestre, conformada solo sobre los tres que lo tienen. Ver 14_dim_semestre.
--
-- es_tendencia marca los anios que entran en la regresion (2021-2025). 2020 se
-- ingesta y se puede ver en el dashboard, pero queda fuera del test de
-- tendencia: fue el anio de ruptura por la pandemia. Esta como atributo y no
-- como filtro en el codigo para que la exclusion sea visible en el modelo.
CREATE OR REPLACE TABLE dim_periodo AS
WITH anios AS (
    SELECT DISTINCT anio FROM silver_ingresante
    UNION SELECT DISTINCT anio FROM silver_matriculado
    UNION SELECT DISTINCT anio FROM silver_postulante
    UNION SELECT DISTINCT anio FROM silver_egresado
    UNION SELECT DISTINCT anio FROM silver_docente
)
SELECT a.anio,
       CAST(a.anio AS VARCHAR(4))                      AS etiqueta,
       a.anio - (SELECT min(anio) FROM anios) + 1      AS orden,
       a.anio = (SELECT max(anio) FROM anios)          AS es_ultimo_anio,
       a.anio BETWEEN p.anio_tendencia_min AND p.anio_tendencia_max AS es_tendencia
FROM anios a
CROSS JOIN ref_parametros p
WHERE a.anio IS NOT NULL
ORDER BY a.anio;
