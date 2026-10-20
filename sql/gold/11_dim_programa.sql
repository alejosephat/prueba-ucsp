-- DIM PROGRAMA. Llave: (codigo_inei, codigo_siu_programa).
-- CODIGO_SIU_PROGRAMA NO es unico a nivel nacional: 288 de 471 codigos se
-- repiten entre universidades. Usarlo solo mezclaria programas de distintas
-- universidades. De ahi la llave compuesta, materializada como programa_sk.
--
-- Homologacion entre universidades: nombre_grupo_3 (83 campos detallados) y
-- nombre_grupo_1 (11 campos amplios) de la clasificacion CINE-UNESCO que la
-- propia fuente de SUNEDU ya trae, contra 2,438 nombres de programa distintos.
--
-- Fuentes de atributos: los CUATRO datasets que alimentan un hecho a grano
-- programa (ingresantes, matricula, postulantes, egresados). NO se incluye
-- carnes universitarios, que tambien trae codigo_siu_programa y clasificacion
-- CINE: anadiria a la dimension programas que ningun hecho referencia, y
-- entonces DISTINCTCOUNT(programa_sk), que es la medida de programas activos
-- de la pregunta 4.1, empezaria a contar programas sin matricula. Una
-- dimension solo debe contener miembros que algun hecho usa.
--
-- Resolucion de atributos divergentes entre periodos: se toma, para CADA
-- atributo por separado, su valor mas reciente NO NULO (max_by ... FILTER).
-- Tomar la fila completa del ultimo anio perderia la clasificacion CINE de los
-- programas que la fuente dejo de reportar en algun periodo: con este criterio
-- los programas sin campo CINE bajan de 415 a 225 de 2,733.
CREATE OR REPLACE TABLE dim_programa AS
WITH todo AS (
    SELECT anio, codigo_inei, codigo_siu_programa, nombre_programa, codigo_grupo_1,
           nombre_grupo_1, codigo_grupo_3, nombre_grupo_3, nivel_academico
    FROM silver_ingresante
    UNION ALL
    SELECT anio, codigo_inei, codigo_siu_programa, nombre_programa, codigo_grupo_1,
           nombre_grupo_1, codigo_grupo_3, nombre_grupo_3, nivel_academico
    FROM silver_matriculado
    UNION ALL
    SELECT anio, codigo_inei, codigo_siu_programa, nombre_programa, codigo_grupo_1,
           nombre_grupo_1, codigo_grupo_3, nombre_grupo_3, nivel_academico
    FROM silver_postulante
    UNION ALL
    SELECT anio, codigo_inei, codigo_siu_programa, nombre_programa, codigo_grupo_1,
           nombre_grupo_1, codigo_grupo_3, nombre_grupo_3, nivel_academico
    FROM silver_egresado
),
consolidado AS (
    SELECT codigo_inei,
           codigo_siu_programa,
           max_by(nombre_programa, anio) FILTER (WHERE nombre_programa IS NOT NULL) AS nombre_programa,
           max_by(codigo_grupo_1,  anio) FILTER (WHERE codigo_grupo_1  IS NOT NULL) AS codigo_grupo_1,
           max_by(nombre_grupo_1,  anio) FILTER (WHERE nombre_grupo_1  IS NOT NULL) AS nombre_grupo_1,
           max_by(codigo_grupo_3,  anio) FILTER (WHERE codigo_grupo_3  IS NOT NULL) AS codigo_grupo_3,
           max_by(nombre_grupo_3,  anio) FILTER (WHERE nombre_grupo_3  IS NOT NULL) AS nombre_grupo_3,
           max_by(nivel_academico, anio) FILTER (WHERE nivel_academico IS NOT NULL) AS nivel_academico
    FROM todo
    WHERE codigo_inei IS NOT NULL AND codigo_siu_programa IS NOT NULL
    GROUP BY 1, 2
)
SELECT md5(codigo_inei || '-' || codigo_siu_programa) AS programa_sk,
       codigo_inei,
       codigo_siu_programa,
       nombre_programa,
       norm(nombre_programa) AS nombre_programa_std,
       codigo_grupo_1,
       nombre_grupo_1,
       codigo_grupo_3,
       nombre_grupo_3,
       -- Etiqueta explicita para que los programas sin clasificar sean visibles
       -- en el dashboard en vez de desaparecer como BLANK.
       coalesce(nombre_grupo_3, 'Sin clasificar CINE') AS campo_estudio,
       nivel_academico
FROM consolidado;
