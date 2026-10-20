-- DIM SEMESTRE. Grano: periodo lectivo dentro del anio.
--
-- POR QUE EXISTE COMO DIMENSION Y NO COMO COLUMNA: tres hechos viven a grano
-- semestral (matricula, egresados, docentes) y tres a grano anual (ingresantes,
-- postulantes, concentracion). Una dimension conformada sobre los tres
-- semestrales permite un slicer unico, y deja dim_periodo en grano ANUAL, que
-- es el grano comun a los seis. Alternativa descartada: una sola dim_periodo
-- semestral de 24 filas, que obligaria a colgar los hechos anuales de la fila
-- "-I" y afirmaria algo falso (que un ingresante ingreso en el semestre I).
--
-- POR QUE HAY UNA TERCERA FILA 'Otro': medido sobre los cuatro archivos de
-- egresados, PERIODO_EGRESO no trae solo 1 y 2. Trae tambien 3 y 4 (2 553
-- filas, 0,43 %) y 4 573 filas sin periodo (0,78 %). Son periodos de egreso
-- extraordinarios. Con solo dos filas, esas 7 126 filas quedarian sin pareja
-- en la dimension y se perderian al relacionar. La fila 0 = 'Otro' las recoge:
-- el 100 % de los egresados queda representado y la rareza es VISIBLE en el
-- dashboard en vez de desaparecer. Matricula y docentes nunca usan esta fila.
--
-- es_serie_anual sale de ref_parametros, que a su vez sale de config.py: es la
-- marca del semestre que define la serie anual comparable. Vive aqui para que
-- el dashboard filtre por un atributo con nombre (dim_semestre[es_serie_anual])
-- en vez de por un literal 1 repartido entre medidas DAX.
CREATE OR REPLACE TABLE dim_semestre AS
SELECT s.semestre,
       s.etiqueta,
       s.semestre = p.semestre_serie_anual AS es_serie_anual
FROM (        SELECT 1 AS semestre, 'I'    AS etiqueta
    UNION ALL SELECT 2,             'II'
    UNION ALL SELECT 0,             'Otro') s
CROSS JOIN ref_parametros p
ORDER BY s.semestre;
