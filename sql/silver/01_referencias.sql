-- Tabla semilla: departamento -> macrorregion. Editable en referencias/macrorregiones.csv.
-- Sur = Arequipa, Cusco, Puno, Moquegua, Tacna, Apurimac, Ayacucho, Madre de Dios
-- (sur andino + selva sur). Ica queda en Centro; ver la justificacion en la PPT.
DROP TABLE IF EXISTS ref_macrorregion;
CREATE TABLE ref_macrorregion AS
SELECT norm(departamento) AS departamento, macrorregion
FROM read_csv('{ruta_macrorregiones}', header=true);

-- Parametros de modelado que config.py y el SQL deben compartir. Existe para
-- que no haya DOS verdades: si SEMESTRE_SERIE_ANUAL cambia en config.py, el
-- SQL lo sigue solo. Sin esta tabla habria un 1 hardcodeado en varios .sql y
-- un 1 en config.py, y nada que los mantenga sincronizados.
DROP TABLE IF EXISTS ref_parametros;
CREATE TABLE ref_parametros AS
SELECT {semestre_serie}::TINYINT  AS semestre_serie_anual,
       {anio_tend_min}::SMALLINT  AS anio_tendencia_min,
       {anio_tend_max}::SMALLINT  AS anio_tendencia_max;

-- Triaje declarado de los nueve datasets del catalogo: hasta que capa llega
-- cada uno y por que. Es una DECLARACION, y el control de calidad #13 la
-- confronta contra la realidad de la base. Si alguien anade un cargador y
-- olvida actualizar este CSV, o lo contrario, el control lo delata.
DROP TABLE IF EXISTS ref_datasets;
CREATE TABLE ref_datasets AS
SELECT * FROM read_csv('{ruta_datasets}', header=true);
