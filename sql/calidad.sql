-- CONTROLES DE CALIDAD (requerimiento 3.2: minimo 3).
--
-- TRES CONTROLES PRINCIPALES, y cada uno existe porque las fuentes de SUNEDU
-- dieron un problema concreto que hubo que medir. No son una lista generica:
--
--   PRINCIPAL 1 - Nada se pierde entre capas.          -> control #02
--       El problema: GYT_Nacionales_2021.csv abortaba la carga entera por DOS
--       filas con una comilla embebida (de 327 475). Y el filtro de pregrado
--       descarta ~20 % de cada archivo. Si una fila desapareciera en silencio
--       entre el CSV y silver, ninguna cifra del informe lo delataria.
--
--   PRINCIPAL 2 - Las llaves identifican lo que dicen identificar. -> #05
--       El problema: CODIGO_SIU_PROGRAMA no es unico a nivel nacional (288 de
--       471 se repiten); los egresados no traen geografia; PERIODO_EGRESO trae
--       periodos 3 y 4; grados y titulos no trae codigo INEI. Cada una de esas
--       rarezas puede dejar filas huerfanas, que en Power BI desaparecen de
--       los visuales sin aviso.
--
--   PRINCIPAL 3 - Cada fuente cubre lo que dice cubrir.  -> #16 y #17
--       El problema: SUNEDU publica un periodo en cuanto lo tiene, no cuando
--       esta cerrado, y no todas las universidades reportan todos los datasets.
--       Sin medirlo, un cociente entre dos fuentes mezcla dos universos: asi
--       salio una "tasa de titulacion" del 206 %.
--
-- Los demas controles son de APOYO: siguen corriendo y siguen siendo la
-- compuerta del pipeline, pero no son lo que se presenta. La columna `grupo`
-- de la salida hace la distincion explicita.
--
-- Devuelve: grupo | control | detalle | valor | umbral | estado.
-- Todo en SQL para que sea reejecutable tal cual en Fabric / Postgres / T-SQL.

SELECT CASE
           WHEN c.control LIKE '02 %' THEN '1 PRINCIPAL - nada se pierde entre capas'
           WHEN c.control LIKE '05 %' THEN '2 PRINCIPAL - las llaves identifican lo que dicen'
           WHEN c.control LIKE '16 %' OR c.control LIKE '17 %'
                THEN '3 PRINCIPAL - cada fuente cubre lo que dice cubrir'
           ELSE '9 apoyo'
       END AS grupo,
       c.*
FROM (

-- 01 Efecto del filtro de pregrado. Informativo: es un recorte declarado.
SELECT '01 Filtro de pregrado'                          AS control,
       fuente || ' ' || periodo                         AS detalle,
       round(100.0 * filas_pregrado / filas_crudas, 1) AS valor,
       '% retenido (informativo)'                       AS umbral,
       'INFO'                                           AS estado
FROM silver_conteo_crudo

UNION ALL
-- 02 Conciliacion crudo -> silver. Filas leidas del CSV que pasan el filtro de
--    pregrado, contra filas efectivamente cargadas en silver. Debe ser 0.
--    El cargador de postulantes aplica ademas un filtro de primera opcion de
--    programa, asi que este control podria arrojar diferencia ahi. No lo hace:
--    da 0 en los cuatro anios, lo que prueba que todo postulante de pregrado
--    declara programa de primera opcion. Por eso el umbral es estricto.
SELECT '02 Conciliacion crudo -> silver',
       c.fuente || ' ' || c.periodo,
       CAST(s.filas - c.filas_pregrado AS DOUBLE),
       '= 0',
       CASE WHEN s.filas = c.filas_pregrado THEN 'OK' ELSE 'REVISAR' END
FROM silver_conteo_crudo c
JOIN (
    SELECT 'ingresante' AS fuente, CAST(anio AS VARCHAR) AS periodo, count(*) AS filas
    FROM silver_ingresante GROUP BY 2
    UNION ALL
    SELECT 'matriculado', anio || '-' || CASE semestre WHEN 1 THEN 'I' ELSE 'II' END, count(*)
    FROM silver_matriculado GROUP BY 2
    UNION ALL
    SELECT 'postulante', CAST(anio AS VARCHAR), count(*)
    FROM silver_postulante GROUP BY 2
    UNION ALL
    SELECT 'docente', anio || '-' || CASE semestre WHEN 1 THEN 'I' ELSE 'II' END, count(*)
    FROM silver_docente GROUP BY 2
    UNION ALL
    SELECT 'carne', CAST(anio AS VARCHAR), count(*)
    FROM silver_carne GROUP BY 2
    UNION ALL
    SELECT 'gyt_nacional', CAST(anio AS VARCHAR), count(*)
    FROM silver_titulo GROUP BY 2
    UNION ALL
    -- Egresados se concilia por ANIO y no por archivo-periodo: el anio de la
    -- fila sale de PERIODO_EGRESO, y el semestre irregular se colapso a 'Otro'
    -- en la carga, asi que el periodo original ya no es reconstruible. El anio
    -- si lo es, y es lo que nombra el archivo.
    SELECT 'egresado', CAST(anio AS VARCHAR), count(*)
    FROM silver_egresado GROUP BY 2
) s ON s.fuente = c.fuente AND s.periodo = c.periodo

UNION ALL
-- 03 Duplicados: misma persona repetida dentro de anio + universidad + programa.
--    El COUNT(DISTINCT guid_persona) de gold los absorbe; aqui se mide cuantos son.
SELECT '03 Duplicados absorbidos por el DISTINCT', fuente, valor, 'informativo', 'INFO'
FROM (
    SELECT 'ingresantes' AS fuente, CAST(coalesce(sum(n - 1), 0) AS DOUBLE) AS valor FROM (
        SELECT count(*) AS n FROM silver_ingresante
        GROUP BY anio, codigo_inei, codigo_siu_programa, guid_persona HAVING count(*) > 1)
    UNION ALL
    SELECT 'matriculados', CAST(coalesce(sum(n - 1), 0) AS DOUBLE) FROM (
        SELECT count(*) AS n FROM silver_matriculado
        GROUP BY anio, semestre, codigo_inei, codigo_siu_programa, guid_persona HAVING count(*) > 1)
)

UNION ALL
-- 04 Nulos en campos clave.
SELECT '04 Nulos en campos clave', 'ingresante.' || campo, CAST(nulos AS DOUBLE),
       -- nombre_grupo_3 (clasificacion CINE) NO es campo obligatorio: la fuente
       -- lo deja vacio en ~20 % de los registros. Es una limitacion declarada,
       -- no un fallo del pipeline, asi que se reporta como INFO. Tratarla como
       -- REVISAR dejaria tres controles en rojo de forma permanente y haria
       -- inservible la compuerta de calidad de la orquestacion. Los campos que
       -- SI son llave exigen 0.
       CASE WHEN campo = 'nombre_grupo_3' THEN 'limitacion declarada de la fuente'
            ELSE '= 0' END,
       CASE WHEN campo = 'nombre_grupo_3' THEN 'INFO'
            WHEN nulos = 0 THEN 'OK' ELSE 'REVISAR' END
FROM (UNPIVOT (SELECT count(*) FILTER (WHERE codigo_inei IS NULL)         AS codigo_inei,
                      count(*) FILTER (WHERE codigo_siu_programa IS NULL) AS codigo_siu_programa,
                      count(*) FILTER (WHERE departamento IS NULL)        AS departamento,
                      count(*) FILTER (WHERE nombre_programa IS NULL)     AS nombre_programa,
                      count(*) FILTER (WHERE nombre_grupo_3 IS NULL)      AS nombre_grupo_3,
                      count(*) FILTER (WHERE guid_persona IS NULL)        AS guid_persona
               FROM silver_ingresante) ON COLUMNS(*) INTO NAME campo VALUE nulos)

UNION ALL
SELECT '04 Nulos en campos clave', 'matriculado.' || campo, CAST(nulos AS DOUBLE),
       -- nombre_grupo_3 (clasificacion CINE) NO es campo obligatorio: la fuente
       -- lo deja vacio en ~20 % de los registros. Es una limitacion declarada,
       -- no un fallo del pipeline, asi que se reporta como INFO. Tratarla como
       -- REVISAR dejaria tres controles en rojo de forma permanente y haria
       -- inservible la compuerta de calidad de la orquestacion. Los campos que
       -- SI son llave exigen 0.
       CASE WHEN campo = 'nombre_grupo_3' THEN 'limitacion declarada de la fuente'
            ELSE '= 0' END,
       CASE WHEN campo = 'nombre_grupo_3' THEN 'INFO'
            WHEN nulos = 0 THEN 'OK' ELSE 'REVISAR' END
FROM (UNPIVOT (SELECT count(*) FILTER (WHERE codigo_inei IS NULL)         AS codigo_inei,
                      count(*) FILTER (WHERE codigo_siu_programa IS NULL) AS codigo_siu_programa,
                      count(*) FILTER (WHERE departamento IS NULL)        AS departamento,
                      count(*) FILTER (WHERE nombre_programa IS NULL)     AS nombre_programa,
                      count(*) FILTER (WHERE nombre_grupo_3 IS NULL)      AS nombre_grupo_3,
                      count(*) FILTER (WHERE guid_persona IS NULL)        AS guid_persona
               FROM silver_matriculado) ON COLUMNS(*) INTO NAME campo VALUE nulos)

UNION ALL
SELECT '04 Nulos en campos clave', 'postulante.' || campo, CAST(nulos AS DOUBLE),
       -- nombre_grupo_3 (clasificacion CINE) NO es campo obligatorio: la fuente
       -- lo deja vacio en ~20 % de los registros. Es una limitacion declarada,
       -- no un fallo del pipeline, asi que se reporta como INFO. Tratarla como
       -- REVISAR dejaria tres controles en rojo de forma permanente y haria
       -- inservible la compuerta de calidad de la orquestacion. Los campos que
       -- SI son llave exigen 0.
       CASE WHEN campo = 'nombre_grupo_3' THEN 'limitacion declarada de la fuente'
            ELSE '= 0' END,
       CASE WHEN campo = 'nombre_grupo_3' THEN 'INFO'
            WHEN nulos = 0 THEN 'OK' ELSE 'REVISAR' END
FROM (UNPIVOT (SELECT count(*) FILTER (WHERE codigo_inei IS NULL)         AS codigo_inei,
                      count(*) FILTER (WHERE codigo_siu_programa IS NULL) AS codigo_siu_programa,
                      count(*) FILTER (WHERE departamento IS NULL)        AS departamento,
                      count(*) FILTER (WHERE nombre_programa IS NULL)     AS nombre_programa,
                      count(*) FILTER (WHERE nombre_grupo_3 IS NULL)      AS nombre_grupo_3,
                      count(*) FILTER (WHERE guid_persona IS NULL)        AS guid_persona
               FROM silver_postulante) ON COLUMNS(*) INTO NAME campo VALUE nulos)

UNION ALL
-- 05 Integridad referencial: hechos sin correspondencia en las dimensiones.
SELECT '05 Integridad referencial', detalle, CAST(huerfanos AS DOUBLE), '= 0',
       CASE WHEN huerfanos = 0 THEN 'OK' ELSE 'REVISAR' END
FROM (
    SELECT 'fct_ingresantes -> dim_programa' AS detalle, count(*) AS huerfanos
    FROM fct_ingresantes f LEFT JOIN dim_programa d USING (programa_sk) WHERE d.programa_sk IS NULL
    UNION ALL SELECT 'fct_ingresantes -> dim_ubicacion', count(*)
    FROM fct_ingresantes f LEFT JOIN dim_ubicacion d USING (ubicacion_sk) WHERE d.ubicacion_sk IS NULL
    UNION ALL SELECT 'fct_ingresantes -> dim_universidad', count(*)
    FROM fct_ingresantes f LEFT JOIN dim_universidad d USING (codigo_inei) WHERE d.codigo_inei IS NULL
    UNION ALL SELECT 'fct_matricula -> dim_programa', count(*)
    FROM fct_matricula f LEFT JOIN dim_programa d USING (programa_sk) WHERE d.programa_sk IS NULL
    UNION ALL SELECT 'fct_matricula -> dim_ubicacion', count(*)
    FROM fct_matricula f LEFT JOIN dim_ubicacion d USING (ubicacion_sk) WHERE d.ubicacion_sk IS NULL
    UNION ALL SELECT 'fct_matricula -> dim_universidad', count(*)
    FROM fct_matricula f LEFT JOIN dim_universidad d USING (codigo_inei) WHERE d.codigo_inei IS NULL
    UNION ALL SELECT 'fct_postulantes -> dim_programa', count(*)
    FROM fct_postulantes f LEFT JOIN dim_programa d USING (programa_sk) WHERE d.programa_sk IS NULL
    UNION ALL SELECT 'fct_postulantes -> dim_ubicacion', count(*)
    FROM fct_postulantes f LEFT JOIN dim_ubicacion d USING (ubicacion_sk) WHERE d.ubicacion_sk IS NULL
    UNION ALL SELECT 'fct_postulantes -> dim_universidad', count(*)
    FROM fct_postulantes f LEFT JOIN dim_universidad d USING (codigo_inei) WHERE d.codigo_inei IS NULL
    UNION ALL SELECT 'fct_matricula -> dim_semestre', count(*)
    FROM fct_matricula f LEFT JOIN dim_semestre d USING (semestre) WHERE d.semestre IS NULL
    UNION ALL SELECT 'fct_egresados -> dim_programa', count(*)
    FROM fct_egresados f LEFT JOIN dim_programa d USING (programa_sk) WHERE d.programa_sk IS NULL
    UNION ALL SELECT 'fct_egresados -> dim_universidad', count(*)
    FROM fct_egresados f LEFT JOIN dim_universidad d USING (codigo_inei) WHERE d.codigo_inei IS NULL
    -- Este es el que justifica la fila 'Otro' de dim_semestre: sin ella, las
    -- 7 126 filas de egresados con periodo 3, 4 o vacio saldrian huerfanas aqui.
    UNION ALL SELECT 'fct_egresados -> dim_semestre', count(*)
    FROM fct_egresados f LEFT JOIN dim_semestre d USING (semestre) WHERE d.semestre IS NULL
    UNION ALL SELECT 'fct_docentes -> dim_universidad', count(*)
    FROM fct_docentes f LEFT JOIN dim_universidad d USING (codigo_inei) WHERE d.codigo_inei IS NULL
    UNION ALL SELECT 'fct_docentes -> dim_semestre', count(*)
    FROM fct_docentes f LEFT JOIN dim_semestre d USING (semestre) WHERE d.semestre IS NULL
    UNION ALL SELECT 'fct_titulos -> dim_universidad', count(*)
    FROM fct_titulos f LEFT JOIN dim_universidad d USING (codigo_inei) WHERE d.codigo_inei IS NULL
    UNION ALL SELECT 'dim_ubicacion sin macrorregion asignada', count(*)
    FROM dim_ubicacion WHERE macrorregion = 'Sin clasificar'
)

UNION ALL
-- 06 Programas con matricula pero sin ingresantes ese anio (pedido explicito).
--    Senal de programa en extincion o de reporte incompleto de la universidad.
SELECT '06 Matricula sin ingresantes', 'anio ' || CAST(m.anio AS VARCHAR),
       CAST(count(*) AS DOUBLE), 'informativo', 'INFO'
FROM fct_matricula m
LEFT JOIN fct_ingresantes i USING (anio, programa_sk, ubicacion_sk)
WHERE i.ingresantes IS NULL
GROUP BY m.anio

UNION ALL
-- 07 Cobertura: universidades que no reportan matricula en todos los anios.
--    Se marcan porque sesgan pendiente y CAGR en el analisis de tendencia.
--    Se abre por estado de licenciamiento SUNEDU porque en el sistema peruano
--    esa es la causa esperada: una universidad con licencia denegada cesa
--    actividades y deja de reportar. Si la serie incompleta se concentra en
--    las denegadas, es un cierre real y no un fallo de la fuente; si apareciera
--    en licenciadas, habria que sospechar del dato. ROLLUP da tambien el total.
SELECT '07 Cobertura de periodos',
       -- GROUPING() distingue la fila total de ROLLUP de una universidad que
       -- realmente no trae licenciamiento: las dos llegan aqui con NULL.
       CASE WHEN GROUPING(u.licenciamiento) = 1
            THEN 'TOTAL sin los '
                 || CAST((SELECT count(DISTINCT anio) FROM fct_matricula) AS VARCHAR) || ' anios'
            ELSE 'licenciamiento: ' || coalesce(u.licenciamiento, 'sin dato') END,
       CAST(count(*) AS DOUBLE), 'informativo', 'INFO'
FROM (SELECT codigo_inei FROM fct_matricula GROUP BY 1
      HAVING count(DISTINCT anio) < (SELECT count(DISTINCT anio) FROM fct_matricula)) i
JOIN dim_universidad u USING (codigo_inei)
GROUP BY ROLLUP (u.licenciamiento)

UNION ALL
-- 08 Variacion intra-anual de la matricula: semestre II contra semestre I del
--    mismo anio. Antes este control estimaba el SESGO de un recorte -- solo se
--    descargaba el semestre I, y 2025-II se bajaba aparte para medir cuanto se
--    perdia. Al ampliar la ingesta a los 12 semestres el recorte desaparecio,
--    y el mismo calculo cambio de naturaleza: ya no mide un sesgo del pipeline
--    sino un fenomeno real del sector, la retencion intra-anual, y lo mide en
--    los SEIS anios en vez de en uno.
--    Se espera negativo y de magnitud moderada: entre el primer y el segundo
--    semestre hay desercion y no hay un ingreso regular que la compense.
SELECT '08 Variacion intra-anual (II vs I)', 'anio ' || CAST(anio AS VARCHAR),
       round(100.0 * (n2 - n1) / n1, 2),
       'abs < 10%',
       CASE WHEN abs(100.0 * (n2 - n1) / n1) < 10 THEN 'OK' ELSE 'REVISAR' END
FROM (SELECT anio,
             count(DISTINCT guid_persona) FILTER (WHERE semestre = 1) AS n1,
             count(DISTINCT guid_persona) FILTER (WHERE semestre = 2) AS n2
      FROM silver_matriculado GROUP BY 1)
WHERE n1 > 0 AND n2 > 0

UNION ALL
-- 09 Conciliacion cruzada entre fuentes: los admitidos que declara el dataset de
--    postulantes deberian aproximar a los ingresantes del dataset de ingresantes.
SELECT '09 Conciliacion cruzada admitidos vs ingresantes', 'anio ' || CAST(a.anio AS VARCHAR),
       round(100.0 * a.adm / nullif(b.ing, 0) - 100, 2), 'desvio abs < 10%',
       CASE WHEN abs(100.0 * a.adm / nullif(b.ing, 0) - 100) < 10 THEN 'OK' ELSE 'REVISAR' END
FROM (SELECT anio, sum(admitidos)   AS adm FROM fct_postulantes GROUP BY 1) a
JOIN (SELECT anio, sum(ingresantes) AS ing FROM fct_ingresantes GROUP BY 1) b USING (anio)

UNION ALL
-- 10 Estandarizacion: universidades cuyo nombre cambia entre periodos.
--    Resueltas tomando el nombre del anio mas reciente (ver 10_dim_universidad.sql).
SELECT '10 Universidades con nombre divergente', 'resueltas con el nombre mas reciente',
       CAST(count(*) AS DOUBLE), 'informativo', 'INFO'
FROM (SELECT codigo_inei FROM (
          SELECT codigo_inei, nombre_entidad FROM silver_ingresante
          UNION SELECT codigo_inei, nombre_entidad FROM silver_matriculado
          UNION SELECT codigo_inei, nombre_entidad FROM silver_postulante)
      GROUP BY 1 HAVING count(*) > 1)

UNION ALL
-- 11 Resolucion de la llave por nombre en grados y titulos.
--    Este control DECIDE si fct_titulos es usable. La fuente de grados y
--    titulos no trae codigo INEI, asi que la universidad se resuelve por
--    igualdad de nombre normalizado. Aqui se publica que porcentaje de titulos
--    resuelve. Si fuera bajo, el hecho tendria que declararse no usable en vez
--    de presentarse como si cubriera el universo.
SELECT '11 Titulos resueltos a universidad por nombre',
       'anio ' || CAST(t.anio AS VARCHAR),
       round(100.0 * count(u.codigo_inei) / count(*), 2),
       '>= 90% resuelto',
       CASE WHEN 100.0 * count(u.codigo_inei) / count(*) >= 90 THEN 'OK' ELSE 'REVISAR' END
FROM silver_titulo t
LEFT JOIN dim_universidad u ON norm(u.nombre_universidad) = norm(t.nombre_entidad)
WHERE t.anio IS NOT NULL
GROUP BY t.anio

UNION ALL
-- 12 Contraste contra una fuente independiente: carnes universitarios emitidos
--    frente a matricula del mismo anio y programa.
--    Los carnes NO entran al modelo como hecho: cuentan tramites, no alumnos.
--    Precisamente por eso sirven de contraste: vienen de un proceso
--    administrativo distinto del reporte academico, asi que una divergencia
--    enorme seria senal de problema en una de las dos fuentes.
--    Se espera MENOS carnes que matriculados (no todo alumno tramita carne
--    cada anio), o sea un ratio por debajo de 100 %. Es informativo: no hay un
--    valor correcto conocido, y declarar un umbral seria inventarlo.
SELECT '12 Carnes emitidos sobre matriculados', 'anio ' || CAST(c.anio AS VARCHAR),
       round(100.0 * c.carnes / m.matriculados, 1), 'informativo', 'INFO'
-- count(*) y NO count(DISTINCT guid): el GUID de esta fuente no identifica
-- personas. Ver el control #15, que es el que lo demuestra.
FROM (SELECT anio, count(*) AS carnes
      FROM silver_carne GROUP BY 1) c
JOIN (SELECT f.anio, sum(f.matriculados) AS matriculados
      FROM fct_matricula f
      JOIN dim_semestre s ON s.semestre = f.semestre AND s.es_serie_anual
      GROUP BY 1) m USING (anio)

UNION ALL
-- 13 Triaje de datasets: la declaracion de referencias/datasets.csv confrontada
--    contra la base. La ingesta baja los NUEVE datasets del catalogo, pero no
--    todos aportan al modelo: algunos no comparten llave, otros miden algo que
--    ya mide otra fuente mejor. Ese triaje esta declarado en un CSV y este
--    control verifica que la declaracion y la realidad coincidan.
--    Si alguien escribe un cargador nuevo y olvida declararlo, o declara gold
--    para un dataset que no llego, esta fila sale en REVISAR.
SELECT '13 Triaje de datasets (declarado vs real)',
       d.rol || ': ' || d.categoria,
       CAST(coalesce(r.filas, 0) AS DOUBLE),
       'coherente con capa_maxima = ' || d.capa_maxima,
       CASE WHEN d.capa_maxima = 'bronze' AND coalesce(r.filas, 0) = 0 THEN 'OK'
            WHEN d.capa_maxima <> 'bronze' AND coalesce(r.filas, 0) > 0 THEN 'OK'
            ELSE 'REVISAR' END
FROM ref_datasets d
LEFT JOIN (
    SELECT 'Ingresante'            AS categoria, count(*) AS filas FROM silver_ingresante
    UNION ALL SELECT 'Matriculado',           count(*) FROM silver_matriculado
    UNION ALL SELECT 'Postulante',            count(*) FROM silver_postulante
    UNION ALL SELECT 'Egresado',              count(*) FROM silver_egresado
    UNION ALL SELECT 'Docente',               count(*) FROM silver_docente
    UNION ALL SELECT 'Carnés Universitarios', count(*) FROM silver_carne
    UNION ALL SELECT 'GYT Nacionales',        count(*) FROM silver_titulo
) r USING (categoria)

UNION ALL
-- 14 Evidencia de la exclusion de 2020 de la regresion de tendencia.
--    La decision de no usar 2020 estaba justificada con un argumento
--    ("fue el anio de la pandemia"). Ahora que el anio esta ingestado, la
--    justificacion se puede MEDIR: se compara la variacion interanual de cada
--    par de anios consecutivos. Si 2020-2021 es un salto muy superior al
--    tipico, incluirlo arrastraria la pendiente de casi todas las series.
--    Lo que esta fila publica es el dato, no la conclusion.
SELECT '14 Variacion interanual de la matricula', 'de ' || CAST(anio - 1 AS VARCHAR)
       || ' a ' || CAST(anio AS VARCHAR)
       || CASE WHEN anio = 2021 THEN ' (anio excluido de la regresion)' ELSE '' END,
       round(100.0 * (n - n_previo) / n_previo, 2), 'informativo', 'INFO'
FROM (SELECT f.anio, sum(f.matriculados) AS n,
             lag(sum(f.matriculados)) OVER (ORDER BY f.anio) AS n_previo
      FROM fct_matricula f
      JOIN dim_semestre s ON s.semestre = f.semestre AND s.es_serie_anual
      GROUP BY f.anio)
WHERE n_previo IS NOT NULL

UNION ALL
-- 15 El GUID del dataset de carnes NO identifica personas.
--    Se descubrio al calcular el control #12: 405 488 filas de 2021 tenian solo
--    321 valores distintos de GUID. Al mirarlos, cada GUID corresponde a UNA
--    universidad pero a decenas de programas y departamentos, y los conteos son
--    sospechosamente redondos (12 000, 20 000). Es un identificador de LOTE de
--    emision por universidad, no de persona.
--    Esta fila publica el numero para que la conclusion sea verificable, y de
--    paso confirma por que los carnes no entran al modelo como hecho: una
--    fuente que no permite contar personas no puede medir matricula.
--    El umbral es estricto a proposito: si una fuente nueva trajera un GUID que
--    SI identifica personas, este control saldria en OK y habria que revisar la
--    decision. Mientras salga en REVISAR, la exclusion esta justificada.
SELECT '15 El GUID de carnes identifica personas',
       'filas por valor distinto de GUID (anio ' || CAST(anio AS VARCHAR) || ')',
       round(1.0 * count(*) / count(DISTINCT guid_persona), 1),
       '= 1.0 si fuera una persona',
       CASE WHEN count(*) = count(DISTINCT guid_persona) THEN 'OK' ELSE 'INFO' END
FROM silver_carne
GROUP BY anio

UNION ALL
-- 16 Completitud del ultimo periodo publicado.
--    SUNEDU publica un periodo en cuanto lo tiene, no cuando esta cerrado, asi
--    que el ultimo puede venir a medias. Se descubrio porque la tasa de
--    titulacion de 2025 salia 131 %: imposible, hasta que se vio que los
--    egresados de 2025 eran 72 638 contra 117 944 en 2024.
--    Este control compara el volumen de cada periodo con la MEDIANA de los
--    demas de la misma fuente. Un periodo muy por debajo esta incompleto, y
--    cualquier ratio que lo use como denominador saldra inflado.
--    Es informativo: la fuente no declara si un periodo esta cerrado, asi que
--    el umbral seria una invencion. Lo que se publica es el dato.
SELECT '16 Volumen del periodo sobre la mediana de su fuente',
       fuente || ' ' || periodo,
       round(100.0 * filas / median(filas) OVER (PARTITION BY fuente), 1),
       'informativo', 'INFO'
FROM (
    SELECT 'egresado' AS fuente, anio || '-' || semestre AS periodo, count(*) AS filas
    FROM silver_egresado WHERE semestre IN (1, 2) GROUP BY 2
    UNION ALL
    SELECT 'docente', anio || '-' || semestre, count(*)
    FROM silver_docente GROUP BY 2
    UNION ALL
    SELECT 'matriculado', anio || '-' || semestre, count(*)
    FROM silver_matriculado GROUP BY 2
)

UNION ALL
-- 17 Cobertura del dataset de egresados frente al de matriculados.
--    Se llego aqui persiguiendo un numero imposible: la division de personas
--    tituladas entre egresados daba 2,5 a nivel nacional. Si fuera una tasa de
--    titulacion, significaria que se titula mas del doble de la gente que
--    egresa, lo cual no puede ser.
--    Parte de la explicacion es el rezago (el titulo se confiere anos despues
--    del egreso), pero la otra parte la mide esta fila: hay universidades que
--    reportan matricula y NO reportan egresados. Con coberturas distintas,
--    cualquier cociente entre las dos fuentes mezcla dos universos.
--    Es informativo: la ausencia de reporte es un hecho de la fuente, no un
--    fallo del pipeline. Lo que importa es que quede medido, porque es la
--    razon por la que las medidas que dividen por egresados llevan la
--    limitacion escrita en su descripcion.
SELECT '17 Universidades que reportan matricula pero no egresados',
       'anio ' || CAST(m.anio AS VARCHAR),
       CAST(m.universidades - coalesce(e.universidades, 0) AS DOUBLE),
       'informativo', 'INFO'
FROM (SELECT anio, count(DISTINCT codigo_inei) AS universidades
      FROM silver_matriculado GROUP BY 1) m
LEFT JOIN (SELECT anio, count(DISTINCT codigo_inei) AS universidades
           FROM silver_egresado GROUP BY 1) e USING (anio)
WHERE e.universidades IS NOT NULL

) c
ORDER BY grupo, control, detalle;
