"""nb_01_transformar — notebook de Microsoft Fabric (PySpark).

Equivalente de 02_transformar.py sobre un Lakehouse: Bronze -> Silver -> Gold.

LA IDEA: no se reescribe el SQL. Este notebook ejecuta EXACTAMENTE los mismos
archivos de sql/silver/ y sql/gold/ que corre la version local con DuckDB. Lo
unico que cambia es lo que rodea al SQL:

  1. La lectura de los CSV: read_csv() de DuckDB -> spark.read.csv().
  2. Las dos macros norm() y limpio(): DuckDB las declara con CREATE MACRO,
     que Spark no tiene. Aqui se registran como UDF de Python.
  3. VARCHAR -> STRING en el DDL de silver (Spark exige longitud en VARCHAR).

Nada mas. El modelo estrella, las granularidades, las reglas de normalizacion
y los agregados son el mismo texto SQL en los dos motores.

ALCANCE: carga los SIETE datasets que llegan a silver, de los nueve que la
ingesta baja. Las dos exclusiones (GYT Extranjeros, que son titulos de
universidades extranjeras y no tiene con que unirse al modelo, y Oferta
universitaria, cuyos atributos ya vienen en las tablas de personas) estan
declaradas en referencias/datasets.csv.

VERIFICACION: las UDF limpio() y norm() se contrastan contra las macros de
DuckDB sobre TODOS los valores distintos de texto de silver -- 8 763 valores de
26 campos -- mas un juego de casos limite. El script esta en el repositorio del
proyecto y se vuelve a correr tras cada cambio.

La primera version de esta verificacion usaba 1 299 valores y daba cero
diferencias. Al ampliarla a los 8 763 aparecieron CUATRO, todas por el trato de
los espacios en blanco, y las macros de DuckDB eran las que estaban mal: su
trim() no quita tabuladores y su \s no cubre el espacio duro chr(160).
Se corrigieron las macros y se reescribieron estas UDF para replicarlas. La
leccion es sobre el metodo: una verificacion sobre una muestra pequena puede dar
cero diferencias y no probar nada.

NO EJECUTADO: este notebook esta escrito para el runtime de Spark de Fabric y
no se ha corrido, porque el proyecto se entrega sin capacidad de Fabric activa
(ver la presentacion tecnica, lamina 3.6). Lo que si esta verificado es la equivalencia
de las UDF y que los .sql que carga son los mismos que produjeron los
resultados entregados.
"""
import csv
import re
import unicodedata
import zipfile
from pathlib import Path

LAGO = Path("/lakehouse/default/Files")
SQL, BRONZE = LAGO / "sql", LAGO / "bronze"
TMP = Path("/tmp/sunedu")
NIVEL_PREGRADO = "Carrera Profesional"
SEMESTRE_SERIE_ANUAL = 1                       # igual que config.py
ANIOS_TENDENCIA = [2021, 2022, 2023, 2024, 2025]
# Mismo mapa que 02_transformar.py. Las categorias ausentes se quedan en
# Files/bronze/ sin pasar a silver, y el motivo esta declarado en
# referencias/datasets.csv, que el control de calidad #13 verifica.
CARGADOR = {"Ingresante": "ingresante", "Matriculado": "matriculado",
            "Postulante": "postulante", "Egresado": "egresado",
            "Docente": "docente", "Carn\u00e9s Universitarios": "carne",
            "GYT Nacionales": "gyt_nacional"}


# ------------------------------------------------- las dos macros, como UDF
# El mismo juego de blancos que la macro blancos() de sql/silver/00_tablas.sql:
# espacio, tabulador, saltos de linea y ESPACIO DURO chr(160).
BLANCOS = "\t\n\x0c\r \xa0"


def limpio(s):
    """Equivalente de la macro limpio(): espacio duro a espacio, recorte de
    blancos en los extremos, y los nulos de la fuente a None."""
    if s is None:
        return None
    s = s.replace("\xa0", " ").strip(BLANCOS)
    return None if s in ("", "<NULL>") else s


def norm(s):
    """Equivalente de la macro norm(): limpio(), sin tildes, mayusculas y
    espacios interiores colapsados.

    OJO con dos detalles, que son la razon por la que esta funcion NO usa
    s.strip() ni r"\s+" a secas:
      - strip() de Python quita mas caracteres que trim() de DuckDB, asi que se
        le pasa el juego explicito.
      - El \s de Python cubre el espacio duro y el de DuckDB (RE2) no, asi que
        la clase de caracteres se escribe a mano para que coincidan. El espacio
        duro ya lo convirtio limpio().
    Sin estos dos cuidados las dos implementaciones divergen en 4 de los 8 763
    valores de texto de silver, y la afirmacion de portabilidad seria falsa."""
    s = limpio(s)
    if s is None:
        return None
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if not unicodedata.combining(c))
    return re.sub(r"[\t\n\x0c\r ]+", " ", s).strip(BLANCOS).upper() or None


spark.udf.register("limpio", limpio)    # noqa: F821  (spark lo inyecta Fabric)
spark.udf.register("norm", norm)        # noqa: F821


def ejecutar(texto, **sustituciones):
    """Ejecuta un .sql de varias sentencias.

    Se salta las que leen archivos con read_csv(): en Spark la vista de entrada
    la crea el DataFrame, no el SQL. Es la unica linea que este notebook ignora
    de los archivos originales.
    """
    for sentencia in texto.format(**sustituciones).split(";"):
        if sentencia.strip() and "read_csv(" not in sentencia:
            spark.sql(sentencia)        # noqa: F821


def leer_csv(ruta, sep="|"):
    """Lector de los planos de TUNI: pipe, cp1252, todo como texto."""
    return (spark.read                  # noqa: F821
            .option("sep", sep).option("header", True)
            .option("encoding", "windows-1252").option("inferSchema", False)
            .csv(str(ruta)))


# ------------------------------------------------------------------ silver
# Mismo DDL que en local. Spark exige longitud en VARCHAR, asi que se usa
# STRING; el resto de tipos (SMALLINT, TINYINT, BIGINT) es identico.
ddl = (SQL / "silver" / "00_tablas.sql").read_text(encoding="utf-8")
ejecutar(ddl.replace("VARCHAR", "STRING"))

# ------------------------------------------------------- bronze -> silver
# Un archivo a la vez, igual que en local: descomprimir, cargar, borrar.
TMP.mkdir(parents=True, exist_ok=True)
with open(BRONZE / "manifiesto.csv", encoding="utf-8") as f:
    for fila in csv.DictReader(f):
        plantilla = CARGADOR.get(fila["categoria"])
        if plantilla is None:
            continue
        with zipfile.ZipFile(BRONZE / fila["archivo"]) as z:
            nombre = z.namelist()[0]
            z.extract(nombre, TMP)
        leer_csv(TMP / nombre).createOrReplaceTempView("crudo")
        ejecutar((SQL / "bronze" / f"{plantilla}.sql").read_text(encoding="utf-8"),
                 ruta="", periodo=fila["periodo"], nivel=NIVEL_PREGRADO)
        (TMP / nombre).unlink()
        print(f"  {fila['categoria']:12s} {fila['periodo']:8s} ok")

# Tabla semilla departamento -> macrorregion. Mismo SQL; solo la lectura cambia.
leer_csv(LAGO / "referencias" / "macrorregiones.csv", sep=",") \
    .createOrReplaceTempView("macrorregiones")
spark.sql("DROP TABLE IF EXISTS ref_macrorregion")                  # noqa: F821
spark.sql("CREATE TABLE ref_macrorregion AS "                       # noqa: F821
          "SELECT norm(departamento) AS departamento, macrorregion "
          "FROM macrorregiones")

# Triaje declarado de los nueve datasets. Lo lee el control de calidad #13.
leer_csv(LAGO / "referencias" / "datasets.csv", sep=",") \
    .createOrReplaceTempView("datasets")
spark.sql("DROP TABLE IF EXISTS ref_datasets")                      # noqa: F821
spark.sql("CREATE TABLE ref_datasets AS SELECT * FROM datasets")    # noqa: F821

# Parametros de modelado. En local salen de config.py por .format(); aqui se
# construyen con los mismos valores, declarados arriba. Es la unica tabla de
# silver que no sale de un .sql literal, y por eso los valores se repiten:
# el notebook no puede importar config.py, que vive fuera del Lakehouse.
spark.sql("DROP TABLE IF EXISTS ref_parametros")                     # noqa: F821
spark.sql(f"CREATE TABLE ref_parametros AS SELECT "                  # noqa: F821
          f"CAST({SEMESTRE_SERIE_ANUAL} AS TINYINT) AS semestre_serie_anual, "
          f"CAST({min(ANIOS_TENDENCIA)} AS SMALLINT) AS anio_tendencia_min, "
          f"CAST({max(ANIOS_TENDENCIA)} AS SMALLINT) AS anio_tendencia_max")

# --------------------------------------------------------- silver -> gold
# Sin una sola modificacion: los mismos archivos, en el mismo orden.
for archivo in sorted((SQL / "gold").glob("*.sql")):
    print(f"  {archivo.name}")
    spark.sql(archivo.read_text(encoding="utf-8"))                  # noqa: F821

print("Listo: tablas Delta en Tables/ del Lakehouse.")
