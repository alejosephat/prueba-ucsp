-- DIM UNIVERSIDAD. Llave: codigo_inei (estable entre periodos).
-- Los nombres de una misma universidad varian entre archivos; se resuelve
-- tomando, para cada atributo, su valor mas reciente NO NULO. Sin fuzzy
-- matching: la llave es el codigo INEI, que la fuente mantiene constante.
CREATE OR REPLACE TABLE dim_universidad AS
WITH todo AS (
    SELECT anio, codigo_inei, nombre_entidad, tipo_entidad, tipo_gestion,
           tipo_constitucion, licenciamiento FROM silver_ingresante
    UNION ALL
    SELECT anio, codigo_inei, nombre_entidad, tipo_entidad, tipo_gestion,
           tipo_constitucion, licenciamiento FROM silver_matriculado
    UNION ALL
    SELECT anio, codigo_inei, nombre_entidad, tipo_entidad, tipo_gestion,
           tipo_constitucion, licenciamiento FROM silver_postulante
),
-- Sede principal: el departamento donde la universidad concentra MAS matricula.
-- Hace falta porque fct_docentes no trae programa ni ubicacion, asi que no se
-- relaciona con dim_ubicacion: sin este atributo, una medida como el ratio
-- alumno/docente de la macrorregion sur no tendria por donde filtrar y
-- devolveria el ratio nacional. La definicion es declarada: "universidad del sur" = aquella
-- cuya sede principal (por volumen de matricula) esta en la macrorregion sur.
sede AS (
    SELECT codigo_inei,
           max_by(departamento, matriculados) AS departamento_sede
    FROM (SELECT m.codigo_inei, m.departamento, count(*) AS matriculados
          FROM silver_matriculado m, ref_parametros p
          WHERE m.semestre = p.semestre_serie_anual AND m.departamento IS NOT NULL
          GROUP BY 1, 2)
    GROUP BY 1
),
consolidado AS (
    SELECT codigo_inei,
           max_by(nombre_entidad,    anio) FILTER (WHERE nombre_entidad    IS NOT NULL) AS nombre_universidad,
           max_by(tipo_entidad,      anio) FILTER (WHERE tipo_entidad      IS NOT NULL) AS tipo_entidad,
           max_by(tipo_gestion,      anio) FILTER (WHERE tipo_gestion      IS NOT NULL) AS tipo_gestion,
           max_by(tipo_constitucion, anio) FILTER (WHERE tipo_constitucion IS NOT NULL) AS tipo_constitucion,
           max_by(licenciamiento,    anio) FILTER (WHERE licenciamiento    IS NOT NULL) AS licenciamiento
    FROM todo
    WHERE codigo_inei IS NOT NULL
    GROUP BY 1
)
SELECT c.codigo_inei,
       c.nombre_universidad,
       c.tipo_entidad,
       c.tipo_gestion,
       c.tipo_constitucion,
       c.licenciamiento,
       s.departamento_sede,
       coalesce(m.macrorregion, 'Sin clasificar')   AS macrorregion_sede,
       coalesce(m.macrorregion, '') = 'Sur'         AS es_macrosur_sede,
       c.codigo_inei = '260000062'                  AS es_ucsp
FROM consolidado c
LEFT JOIN sede s             ON s.codigo_inei = c.codigo_inei
LEFT JOIN ref_macrorregion m ON m.departamento = norm(s.departamento_sede);
