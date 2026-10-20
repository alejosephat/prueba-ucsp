-- HECHO TITULOS (grados y titulos nacionales)
-- GRANULARIDAD: una fila por anio de resolucion x universidad.
--
-- ESTA TABLA SE CONSTRUYE CON UNA LLAVE RESUELTA POR NOMBRE, y eso obliga a
-- justificarlo porque el resto del proyecto rechaza el fuzzy matching.
-- La diferencia es que aqui NO hay fuzzy matching: hay un join de IGUALDAD
-- sobre el nombre normalizado con norm, es decir sin tildes, en mayusculas y
-- con los espacios colapsados. Es la misma funcion que normaliza las demas
-- llaves de texto del modelo. Un nombre que no coincide exactamente no se
-- fuerza: se queda fuera y se cuenta. El control de calidad #11 publica la
-- tasa de resolucion, de modo que el lector ve cuanto cubre la llave.
--
-- POR QUE SE ACEPTA ESTA EXCEPCION: es la unica fuente del portal que mide
-- titulacion EFECTIVA (obtener el diploma) y no egreso (terminar los cursos).
-- La brecha entre egresar y titularse es un indicador real de eficiencia, y no
-- hay otra manera de obtenerlo. El grano es universidad-anio, no programa,
-- porque NOMBRE_CARRERA es texto libre: resolverlo a programa SI exigiria
-- fuzzy matching sobre 2 438 nombres distintos, y ahi se traza la linea.
CREATE OR REPLACE TABLE fct_titulos AS
SELECT t.anio,
       u.codigo_inei,
       count(*)                                                AS titulos,
       -- MEDIDO: 437 872 personas tienen DOS titulos (el grado de bachiller y
       -- el titulo profesional) y 4 153 tienen tres o mas. Asi que count(*)
       -- cuenta EVENTOS de titulacion, no personas, y cualquier cociente contra
       -- egresados saldria al doble. Se guardan las dos cifras: los eventos,
       -- que es lo que la fuente mide, y las personas, que es lo unico
       -- comparable con un conteo de egresados.
       count(DISTINCT t.guid_persona)                          AS personas,
       count(*) FILTER (WHERE norm(t.abreviatura_grado) = 'B')  AS bachilleres,
       count(*) FILTER (WHERE norm(t.abreviatura_grado) = 'T')  AS titulados,
       round(median(t.anios_estudio), 2)                        AS anios_estudio_mediana
FROM silver_titulo t
JOIN dim_universidad u ON norm(u.nombre_universidad) = norm(t.nombre_entidad)
WHERE t.anio IS NOT NULL
GROUP BY 1, 2;
