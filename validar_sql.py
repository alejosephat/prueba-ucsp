"""Valida el SQL de silver y gold contra un esquema VACIO, en memoria.

Uso:  python validar_sql.py        (no necesita data/, corre en 3 segundos)

Existe por una razon practica: la carga real tarda unos 35 minutos, y un error
de sintaxis o una columna mal escrita en sql/gold/ no se descubriria hasta el
final. Este script crea las tablas de silver vacias, ejecuta todo el SQL de
gold y la consulta de calidad, y falla con el archivo y el mensaje exactos.
Se corre antes de cada carga larga.

Comprueba sintaxis y referencias a columnas sin esperar los 35 minutos que
tarda la carga real. Las tablas quedan vacias, asi que no valida resultados:
valida que el SQL se pueda ejecutar.
"""
import sys
import duckdb
from pathlib import Path

RAIZ = Path(__file__).parent
SQL = RAIZ / "sql"

con = duckdb.connect()
con.execute("INSTALL encodings; LOAD encodings;")

# silver: DDL completo (macros + tablas vacias)
con.execute((SQL / "silver" / "00_tablas.sql").read_text(encoding="utf-8"))
print("silver/00_tablas.sql           ok")

# referencias: se sustituyen las rutas igual que en 02_transformar.py. Los
# parametros se pasan a mano y no desde config.py a proposito: asi el script
# tambien valida que las claves de .format() del .sql sigan siendo las que
# 02_transformar.py le pasa. Si alguien anade un {placeholder} y olvida
# pasarlo, este script falla antes que la carga.
ref = (SQL / "silver" / "01_referencias.sql").read_text(encoding="utf-8")
con.execute(ref.format(
    ruta_macrorregiones=(RAIZ / "referencias" / "macrorregiones.csv").as_posix(),
    ruta_datasets=(RAIZ / "referencias" / "datasets.csv").as_posix(),
    semestre_serie=1, anio_tend_min=2021, anio_tend_max=2025))
print("silver/01_referencias.sql      ok")

fallos = 0
for archivo in sorted((SQL / "gold").glob("*.sql")):
    try:
        con.execute(archivo.read_text(encoding="utf-8"))
        n = con.execute(f"SELECT count(*) FROM {archivo.stem.split('_', 1)[1]}").fetchone()[0]
        print(f"gold/{archivo.name:28s} ok  ({n} filas, esquema vacio)")
    except Exception as e:
        print(f"gold/{archivo.name:28s} FALLA  {str(e).splitlines()[0][:110]}")
        fallos += 1

# calidad: la consulta completa
try:
    con.execute((SQL / "calidad.sql").read_text(encoding="utf-8")).fetchall()
    print("calidad.sql                    ok")
except Exception as e:
    print(f"calidad.sql                    FALLA  {str(e).splitlines()[0][:110]}")
    fallos += 1

print(f"\n{fallos} fallos")
sys.exit(1 if fallos else 0)
