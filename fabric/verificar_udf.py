"""Contrasta las UDF de Python del notebook de Fabric contra las macros de DuckDB.

Uso:  python fabric/verificar_udf.py    (requiere data/sunedu.duckdb construida)

Es la prueba de la afirmacion central de fabric/README.md: que el notebook de
Spark produce lo mismo que el pipeline local. Sin este script esa afirmacion
seria una promesa.

Se ejecutan las dos implementaciones sobre TODOS los valores distintos de texto
que hay en silver, y se comparan uno a uno. Si difieren, el notebook no es
equivalente al pipeline local y la afirmacion de portabilidad seria falsa.
"""
import duckdb
from pathlib import Path

RAIZ = Path(__file__).parent.parent


# --- las UDF, tomadas del propio notebook -----------------------------------
# No se copian aqui: se extraen del archivo que se entrega. Si alguien edita el
# notebook y no esta de acuerdo con las macros, este script lo detecta. Una
# copia en el test podria quedar desincronizada del codigo real, que es
# justamente el error que este script existe para evitar.
FUENTE = (RAIZ / "fabric" / "nb_01_transformar.py").read_text(encoding="utf-8")


class SparkFalso:
    """El notebook esta escrito para el runtime de Fabric, que inyecta `spark`.
    Aqui solo hacen falta las dos funciones, asi que se ejecuta el archivo hasta
    justo antes del registro de las UDF."""
    class udf:
        register = staticmethod(lambda *a, **k: None)


ns = {"spark": SparkFalso()}
exec(FUENTE[:FUENTE.index("spark.udf.register")], ns)
norm, limpio = ns["norm"], ns["limpio"]
print("UDF extraidas de fabric/nb_01_transformar.py")


# --- los valores reales -----------------------------------------------------
CAMPOS = [
    ("silver_ingresante", "departamento"), ("silver_ingresante", "provincia"),
    ("silver_ingresante", "nombre_programa"), ("silver_ingresante", "nombre_entidad"),
    ("silver_ingresante", "nivel_academico"), ("silver_ingresante", "nombre_grupo_3"),
    ("silver_matriculado", "departamento"), ("silver_matriculado", "provincia"),
    ("silver_matriculado", "nombre_programa"), ("silver_matriculado", "nombre_entidad"),
    ("silver_postulante", "modalidad_ingreso"), ("silver_postulante", "nombre_programa"),
    ("silver_egresado", "nombre_programa"), ("silver_egresado", "nombre_entidad"),
    ("silver_docente", "nombre_entidad"), ("silver_docente", "regimen_dedicacion"),
    ("silver_docente", "tipo_grado_titulo"), ("silver_docente", "condicion_laboral"),
    ("silver_carne", "nombre_programa"), ("silver_carne", "departamento"),
    ("silver_carne", "nivel_academico"), ("silver_carne", "provincia"),
    ("silver_titulo", "nombre_entidad"), ("silver_titulo", "nombre_carrera"),
    ("silver_titulo", "departamento_sede"), ("silver_titulo", "modalidad_obtencion"),
]

# Dos conexiones a proposito:
#   datos  -> la base construida, de donde salen los valores reales
#   con    -> una base en memoria con las macros recien leidas del .sql
# Si se usara la base para evaluar las macros, se estarian probando las que
# quedaron guardadas en su catalogo en la ultima carga, no las del codigo
# fuente actual. Es un error facil: el primer intento de este script lo tenia.
datos = duckdb.connect(str(RAIZ / "data" / "sunedu.duckdb"), read_only=True)
con = duckdb.connect()
con.execute("INSTALL encodings; LOAD encodings;")
ddl = (RAIZ / "sql" / "silver" / "00_tablas.sql").read_text(encoding="utf-8")
con.execute(ddl[:ddl.index("DROP TABLE")])          # solo las macros
print("macros leidas de sql/silver/00_tablas.sql")

tablas = {r[0] for r in datos.execute(
    "SELECT table_name FROM duckdb_tables() WHERE table_name LIKE 'silver%'").fetchall()}

valores = set()
usados = []
for tabla, campo in CAMPOS:
    if tabla not in tablas:
        continue
    try:
        v = datos.execute(f"SELECT DISTINCT {campo} FROM {tabla} "
                          f"WHERE {campo} IS NOT NULL").fetchall()
    except Exception as e:
        print(f"  (omitido {tabla}.{campo}: {str(e).splitlines()[0][:50]})")
        continue
    valores |= {x[0] for x in v}
    usados.append(f"{tabla}.{campo}")

# Casos limite que la fuente puede traer y que las macros deben tratar igual
valores |= {"<NULL>", "", "   ", "  DOBLE   ESPACIO  ", "Ñandú", "ÁÉÍÓÚ", "ñ", "\tTAB\t"}
valores = sorted(valores)
print(f"{len(valores):,} valores distintos, de {len(usados)} campos de silver")

# --- comparar --------------------------------------------------------------
dif_norm, dif_limpio = [], []
for v in valores:
    d_n, d_l = con.execute("SELECT norm(?), limpio(?)", [v, v]).fetchone()
    p_n, p_l = norm(v), limpio(v)
    if d_n != p_n:
        dif_norm.append((v, d_n, p_n))
    if d_l != p_l:
        dif_limpio.append((v, d_l, p_l))

print(f"\nnorm():    {len(dif_norm)} diferencias")
for v, d, pp in dif_norm[:8]:
    print(f"   {v!r:40.40}  duckdb={d!r:28.28}  python={pp!r}")
print(f"limpio():  {len(dif_limpio)} diferencias")
for v, d, pp in dif_limpio[:8]:
    print(f"   {v!r:40.40}  duckdb={d!r:28.28}  python={pp!r}")

ok = not dif_norm and not dif_limpio
print(f"\n{'EQUIVALENTES' if ok else 'NO EQUIVALENTES'} sobre {len(valores):,} valores")
print(f"\nPARA LA DOCUMENTACION: {len(valores):,} valores distintos, "
      f"{len(usados)} campos, cero diferencias" if ok else "REVISAR")
con.close()
datos.close()
