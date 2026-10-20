"""Bronze -> Silver -> Gold con DuckDB.

Python solo orquesta: abre la base, recorre los zips y ejecuta los .sql.
Toda la logica de transformacion vive en sql/ (portable a Postgres/T-SQL/Spark).

Procesa un archivo a la vez (descomprimir -> cargar -> borrar el CSV) para que
el pico de disco sea el archivo mas grande (601 MB) y no la suma (unos 11 GB).
"""
import csv
import sys
import zipfile

import duckdb

from config import (ANIOS_TENDENCIA, BRONZE, DUCKDB, GOLD, NIVEL_PREGRADO,
                    REFERENCIAS, SEMESTRE_SERIE_ANUAL, SQL, TMP)

# Categoria del catalogo TUNI -> plantilla de sql/bronze/ que la carga.
# Las categorias que NO aparecen aqui se descargan a bronze pero no pasan a
# silver, y el motivo esta declarado:
#   "Oferta universitaria" -> catalogo institucional; su contenido util
#       (gestion, licenciamiento, sede) ya viene en las tablas de personas.
#   "GYT Extranjeros"      -> reconocimiento de titulos obtenidos en
#       universidades EXTRANJERAS. No tiene universidad peruana, asi que no hay
#       con que unirlo al modelo. Ademas viene en UTF-16, no en cp1252 como el
#       resto del portal. Se conserva en bronze por trazabilidad.
CARGADOR = {"Ingresante": "ingresante",
            "Matriculado": "matriculado",
            "Postulante": "postulante",
            "Egresado": "egresado",
            "Docente": "docente",
            "Carnés Universitarios": "carne",
            "GYT Nacionales": "gyt_nacional"}


def cargar_bronze(con, fila):
    """Descomprime un zip, lo inserta en silver y borra el CSV."""
    plantilla = CARGADOR.get(fila["categoria"])
    if plantilla is None:
        return

    zip_ruta = BRONZE / fila["archivo"]
    with zipfile.ZipFile(zip_ruta) as z:
        nombre_csv = z.namelist()[0]
        z.extract(nombre_csv, TMP)
    csv_ruta = TMP / nombre_csv

    print(f"  {fila['categoria']:12s} {fila['periodo']:8s} "
          f"{csv_ruta.stat().st_size / 1048576:6.0f} MB ...", end="", flush=True)
    sql = (SQL / "bronze" / f"{plantilla}.sql").read_text(encoding="utf-8")
    con.execute(sql.format(ruta=csv_ruta.as_posix(), periodo=fila["periodo"],
                           nivel=NIVEL_PREGRADO))
    csv_ruta.unlink()
    print(" ok")


def main():
    # --solo-gold reconstruye dimensiones y hechos sobre el silver ya cargado,
    # sin volver a leer los CSV. Util al iterar sobre las reglas del modelo.
    solo_gold = "--solo-gold" in sys.argv
    TMP.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)
    if not solo_gold:
        DUCKDB.unlink(missing_ok=True)
    con = duckdb.connect(str(DUCKDB))
    # Los CSV de TUNI son cp1252 (usan 0x96 = guion largo, fuera de ISO-8859-1).
    con.execute("INSTALL encodings; LOAD encodings;")

    if not solo_gold:
        print("SILVER: creando tablas")
        con.execute((SQL / "silver" / "00_tablas.sql").read_text(encoding="utf-8"))

        print("BRONZE -> SILVER")
        with open(BRONZE / "manifiesto.csv", encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                cargar_bronze(con, fila)

    # Siempre: es barato y recoge cualquier edicion de referencias/macrorregiones.csv.
    con.execute((SQL / "silver" / "01_referencias.sql").read_text(encoding="utf-8")
                .format(ruta_macrorregiones=(REFERENCIAS / "macrorregiones.csv").as_posix(),
                        semestre_serie=SEMESTRE_SERIE_ANUAL,
                        anio_tend_min=min(ANIOS_TENDENCIA),
                        anio_tend_max=max(ANIOS_TENDENCIA),
                        ruta_datasets=(REFERENCIAS / "datasets.csv").as_posix()))

    print("SILVER -> GOLD")
    for archivo in sorted((SQL / "gold").glob("*.sql")):
        print(f"  {archivo.name}")
        con.execute(archivo.read_text(encoding="utf-8"))

    print("GOLD -> parquet")
    tablas = [t[0] for t in con.execute(
        "SELECT table_name FROM duckdb_tables() "
        "WHERE table_name LIKE 'dim%' OR table_name LIKE 'fct%' ORDER BY 1").fetchall()]
    for tabla in tablas:
        destino = GOLD / f"{tabla}.parquet"
        # ORDER BY ALL no es decorativo: sin el, el orden de las filas del
        # parquet depende de como DuckDB reparta la agregacion entre hilos, y
        # dos corridas con los mismos datos producen archivos con bytes
        # distintos. Ordenar canonicamente los hace comparables con un diff,
        # que es lo que convierte "es reproducible" en algo verificable por
        # quien reciba el proyecto. Sobre tablas de decenas de miles de filas
        # el coste del sort es despreciable.
        con.execute(f"COPY (SELECT * FROM {tabla} ORDER BY ALL) "
                    f"TO '{destino.as_posix()}' (FORMAT parquet)")
        n = con.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]
        print(f"  {tabla:28s} {n:>9,} filas")

    con.close()
    print(f"\nListo. Base en {DUCKDB}, parquets en {GOLD}")


if __name__ == "__main__":
    main()
