# Portabilidad del SQL

DuckDB es el motor de **desarrollo**, no una dependencia del diseño. Este documento
mide cuánto trabajo cuesta llevar la lógica a otro motor. No estima: cuenta líneas.

## El argumento central

En producción la UCSP no ingiere CSV de SharePoint: ingiere de su SIS/ERP, que ya vive
en SQL Server o PostgreSQL. Es decir, **la única capa atada a DuckDB —`sql/bronze/`, la
lectura de archivos planos— es exactamente la capa que desaparece** en el entorno real.

Por eso la medición se hace sobre `sql/silver/` y `sql/gold/`, que son las que sí viajan.

## Lo medido

**397 líneas de código** en `sql/silver/` y `sql/gold/` (163 en silver, 234 en gold), sin contar comentarios ni líneas en blanco.

| Motor destino | Líneas a traducir | % | De ellas, en `sql/gold/` |
|---|---|---|---|
| Spark | **5** | 1,3 % | **0** |
| PostgreSQL | **30** | 7,6 % | **25** |
| SQL Server / T-SQL | **45** | 11,3 % | **37** |

El orden no es casual. Spark es el más barato porque el SQL se escribió para que los dos
motores aceptaran el mismo texto: `arg_max()` se escribió como `max_by()` y el único
`CAST(... AS VARCHAR)` se tipó como `VARCHAR(4)` precisamente por eso (ver decisión G5).
T-SQL es el más caro porque difiere en la sintaxis de concatenación (`||` contra `+`),
en el *cast* (`::`) y en `FILTER (WHERE ...)`, que aparecen repartidos por todo el código.

## Qué hay que cambiar, construcción por construcción

Una línea puede tener dos construcciones no portables a la vez (por ejemplo `md5(a || '-' || b)`),
y entonces se cuenta **una sola vez**, bajo la primera: lo que se mide es cuántas líneas hay que
tocar, no cuántas sustituciones hay que hacer dentro de ellas.

### Spark

| Hay que escribir en su lugar | Líneas |
|---|---|
| funcion de Python registrada con spark.udf.register | 2 |
| spark.read.csv() + createOrReplaceTempView | 2 |
| dentro de la UDF: unicodedata.normalize('NFD', ...) | 1 |

### PostgreSQL

| Hay que escribir en su lugar | Líneas |
|---|---|
| DROP TABLE IF EXISTS + CREATE TABLE AS | 12 |
| (array_agg(x ORDER BY anio DESC NULLS LAST))[1] | 12 |
| CREATE OR REPLACE FUNCTION ... LANGUAGE sql | 2 |
| COPY ... FROM | 2 |
| unaccent() (extension unaccent) | 1 |
| percentile_cont(0.5) WITHIN GROUP (ORDER BY ...) | 1 |

### SQL Server / T-SQL

| Hay que escribir en su lugar | Líneas |
|---|---|
| DROP TABLE IF EXISTS + SELECT ... INTO | 12 |
| subconsulta con ROW_NUMBER() OVER (ORDER BY anio DESC) | 12 |
| CONVERT(CHAR(32), HASHBYTES('MD5', ...), 2) | 9 |
| CAST(... AS tipo) | 3 |
| CASE WHEN dentro del agregado | 3 |
| funcion escalar con CREATE FUNCTION | 2 |
| BULK INSERT / OPENROWSET | 2 |
| COLLATE Latin1_General_CI_AI | 1 |
| PERCENTILE_CONT(0.5) OVER (...) | 1 |

## Tabla de equivalencias

| Construcción | DuckDB (desarrollo) | PostgreSQL | SQL Server / Fabric Warehouse |
|---|---|---|---|
| Carga de plano | `read_csv(..., delim='\|')` | `COPY ... FROM` | `BULK INSERT` / `OPENROWSET` |
| Hash de llave sustituta | `md5(a‖'-'‖b)` | `md5(...)` | `HASHBYTES('MD5', ...)` |
| Último valor no nulo | `max_by(x, anio) FILTER (...)` | `array_agg(... ORDER BY)` | `ROW_NUMBER()` en subconsulta |
| Quitar tildes | `strip_accents()` | `unaccent()` | `COLLATE Latin1_General_CI_AI` |
| Mediana | `median()` | `percentile_cont(0.5) WITHIN GROUP` | `PERCENTILE_CONT(0.5) OVER` |
| Agregado condicional | `FILTER (WHERE ...)` | `FILTER (WHERE ...)` | `CASE WHEN` dentro del agregado |
| Materializar | `CREATE OR REPLACE TABLE` | `DROP` + `CREATE TABLE AS` | `DROP` + `SELECT ... INTO` |
| Concatenar | `\|\|` | `\|\|` | `+` |
| CTE, ventanas, `COUNT(DISTINCT)`, `CASE`, joins, `ROLLUP` | — | **idéntico** | **idéntico** |

## Lo que se entrega además

`sql/ddl_postgres.sql` y `sql/ddl_sqlserver.sql`: el DDL completo del modelo estrella
—13 tablas con tipos, claves primarias y foráneas— listo para crear el esquema en el
entorno institucional. Incluyen el comentario que advierte que `codigo_inei` en
`dim_programa` es FK en la base pero **no** debe relacionarse en el modelo semántico.

## Nota sobre Fabric

El *SQL Analytics Endpoint* del Lakehouse y el Warehouse de Fabric son **T-SQL**. La
columna de SQL Server de la tabla de equivalencias no es un ejercicio teórico: es
literalmente lo que se ejecuta al consultar el modelo desde fuera del notebook. La ruta
de los notebooks, en cambio, es la columna de Spark — la más barata de las tres.
