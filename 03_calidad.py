"""Ejecuta los controles de calidad y guarda el resultado.

Toda la logica esta en sql/calidad.sql: este script solo lo corre y lo exporta,
para que los mismos controles se puedan ejecutar tal cual en Fabric o SQL Server.

La salida en consola NO vuelca las 222 filas: lidera con los TRES controles
principales -- los que estan atados a los problemas reales que dieron las
fuentes -- y resume el resto. El CSV si lleva todo, porque es la evidencia.
"""
import duckdb

from config import DUCKDB, SALIDAS, SQL

DESTINO = SALIDAS / "calidad" / "qc_resultados.csv"


def veredicto(sub):
    """Una linea por control: cuantas filas trae y la peor noticia que da."""
    revisar = (sub["estado"] == "REVISAR").sum()
    if revisar:
        return f"{len(sub):>4} filas   REVISAR ({revisar})"
    if (sub["estado"] == "OK").any():
        return f"{len(sub):>4} filas   OK"
    return f"{len(sub):>4} filas   informativo"


def main():
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB), read_only=True)
    df = con.execute((SQL / "calidad.sql").read_text(encoding="utf-8")).df()
    con.close()
    df.to_csv(DESTINO, index=False, encoding="utf-8-sig")

    for grupo in sorted(df["grupo"].unique()):
        g = df[df["grupo"] == grupo]
        print(f"\n{grupo[2:].upper()}")
        for control in sorted(g["control"].unique()):
            sub = g[g["control"] == control]
            print(f"  {control:<50s} {veredicto(sub)}")

    print(f"\n{df['control'].nunique()} controles | {len(df)} filas | "
          + " | ".join(f"{e}: {n}" for e, n in df["estado"].value_counts().items()))

    fallos = df[df["estado"] == "REVISAR"]
    if len(fallos):
        print(f"\n{len(fallos)} fila(s) en REVISAR:")
        print(fallos[["control", "detalle", "valor", "umbral"]].to_string(index=False))
    print(f"\nEvidencia completa en {DESTINO}")


if __name__ == "__main__":
    main()
