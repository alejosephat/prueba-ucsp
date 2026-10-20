"""Componente estadistico: tendencia de ingresantes y matricula por programa.

TECNICA: regresion lineal simple (OLS) de log(y) contra el anio, 2021-2025, por
programa, sobre DOS series: ingresantes y matricula. Sustento, condiciones de
aplicabilidad y limitaciones en docs/componente_estadistico.md.

Por que en logaritmo: la pendiente de log(y) ~ anio es la tasa de crecimiento
anual compuesta (CAGR = exp(pendiente) - 1). Un programa que pasa de 80 a 120
alumnos y otro que pasa de 800 a 1200 tienen la misma pendiente; en niveles, el
grande dominaria siempre.

Por que dos series y no solo matricula: la matricula es un STOCK que acumula
cohortes. Un programa abierto en 2020 llena sus cinco anios de alumnos aunque
su ingreso caiga, y la regresion de matricula sola lo reporta como crecimiento.
Medido en la UCSP: Arquitectura sube +30 % anual en matricula mientras su
ingreso baja de 261 a 217. El ingreso es el indicador adelantado de demanda; la
matricula lo confirma con rezago. La pregunta 4.3 pide las dos.

VENTANA: 2021-2025. 2020 esta cargado y visible en el dashboard, pero fuera del
test: su rebote post-pandemia arrastraria la pendiente de casi todos los
programas (decision B2b, control de calidad #14).
"""
import duckdb
import numpy as np
import pandas as pd
from scipy import stats

from config import (ANIOS_TENDENCIA, CAGR_MIN, DUCKDB, GOLD,
                    MIN_ANIOS_TENDENCIA, P_VALOR_MAX, UCSP)

# Serie anual por programa. {semestre} existe por la matricula: el hecho trae
# los 12 semestres, y sin fijar uno por anio quien estuvo matriculado todo el
# anio contaria dos veces. Ingresantes es anual en la fuente y no lo necesita.
POR_PROGRAMA = """
SELECT f.programa_sk AS llave, f.anio, sum(f.{medida}) AS valor
FROM {hecho} f
JOIN dim_periodo t ON t.anio = f.anio AND t.es_tendencia
{semestre}
GROUP BY 1, 2
ORDER BY 1, 2
"""

# Benchmark de la 4.3: el mismo campo CINE (nivel 3) en la macrorregion sur,
# EXCLUYENDO a la UCSP. Sin esa exclusion se compararia contra una serie que
# la contiene.
POR_CAMPO_SUR = """
SELECT p.nombre_grupo_3 AS llave, f.anio, sum(f.{medida}) AS valor
FROM {hecho} f
JOIN dim_periodo   t ON t.anio = f.anio AND t.es_tendencia
{semestre}
JOIN dim_programa  p ON p.programa_sk  = f.programa_sk
JOIN dim_ubicacion u ON u.ubicacion_sk = f.ubicacion_sk
WHERE u.es_macrosur
  AND f.codigo_inei <> '{ucsp}'
  AND p.nombre_grupo_3 IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2
"""

# sufijo de columna -> (hecho, medida, filtro de semestre)
SERIES = {
    "ing": ("fct_ingresantes", "ingresantes", ""),
    "mat": ("fct_matricula", "matriculados",
            "JOIN dim_semestre s ON s.semestre = f.semestre AND s.es_serie_anual"),
}

SENTIDO = {"Crecimiento sostenido": 1, "Caida sostenida": -1,
           "Sin tendencia sostenida": 0}


def ols_log(anios, valores):
    """Pendiente de log(valores) ~ anios. Devuelve (cagr, p_valor, n)."""
    n = len(anios)
    if n < MIN_ANIOS_TENDENCIA or min(valores) <= 0:
        return np.nan, np.nan, n

    x = np.asarray(anios, dtype=float)
    y = np.log(np.asarray(valores, dtype=float))
    sxx = ((x - x.mean()) ** 2).sum()
    pendiente = ((x - x.mean()) * (y - y.mean())).sum() / sxx
    residuos = y - (y.mean() + pendiente * (x - x.mean()))
    error_estandar = np.sqrt((residuos ** 2).sum() / (n - 2) / sxx)

    if error_estandar == 0:                       # ajuste perfecto
        p_valor = 0.0
    else:
        p_valor = 2 * stats.t.sf(abs(pendiente / error_estandar), df=n - 2)
    return float(np.exp(pendiente) - 1), float(p_valor), n


def clasificar(cagr, p_valor, n):
    """Tendencia sostenida = serie suficiente + regularidad + magnitud relevante.

    Las tres a la vez: >= 4 anios con dato, p < 0,05 (la pendiente no es
    atribuible al azar) y |CAGR| >= 3 % (el cambio importa en la practica).
    Todo lo demas es "sin tendencia sostenida", que es lo que la 4.3 necesita
    saber. No se separa "estable" de "irregular": con cinco puntos esa
    distincion exige un tercer umbral sobre la dispersion y medido, el 57 % de
    los ingresos con pendiente plana oscila mas de un 10 % alrededor de ella.

    No se usa el R2: mide que parte de la variacion explica la pendiente, y en
    una serie plana es ~0 por construccion, por estable que sea.
    """
    if n < MIN_ANIOS_TENDENCIA or np.isnan(cagr):
        return "Serie insuficiente"
    if p_valor < P_VALOR_MAX and abs(cagr) >= CAGR_MIN:
        return "Crecimiento sostenido" if cagr > 0 else "Caida sostenida"
    return "Sin tendencia sostenida"


def tendencias(df):
    """Aplica ols_log a cada serie (una por llave) y la clasifica."""
    filas = []
    for llave, g in df.groupby("llave", sort=False):
        cagr, p_valor, n = ols_log(g["anio"].tolist(), g["valor"].tolist())
        ultimo = g.loc[g["anio"] == max(ANIOS_TENDENCIA), "valor"].sum()
        filas.append({"llave": llave, "anios": n, "cagr": cagr, "p_valor": p_valor,
                      "tendencia": clasificar(cagr, p_valor, n),
                      "ultimo_anio": int(ultimo)})
    return pd.DataFrame(filas)


def cuadrante(cagr, cagr_campo):
    """Posicion del programa frente a su campo en el sur (pregunta 4.3)."""
    if np.isnan(cagr) or np.isnan(cagr_campo):
        return "Sin comparable"
    if cagr > 0 and cagr_campo > 0:
        return ("Gana cuota en campo creciente" if cagr >= cagr_campo
                else "Pierde cuota en campo creciente")
    if cagr > 0:
        return "Crece contra un campo que cae"
    if cagr_campo > 0:
        return "Cae en un campo que crece"
    return "Cae con su campo"


def lectura(tendencia_ing, tendencia_mat):
    """Cruza las dos series. Manda el ingreso, que es el indicador adelantado."""
    ing, mat = SENTIDO.get(tendencia_ing), SENTIDO.get(tendencia_mat)
    if ing is None or mat is None:
        return "Serie insuficiente"
    if ing == 1:
        return "Crecimiento confirmado" if mat == 1 else "Ingreso en alza"
    if ing == -1:
        return "Caida confirmada" if mat == -1 else "Alerta: cae el ingreso"
    if mat == 1:
        return "Crece la matricula, no el ingreso"
    if mat == -1:
        return "Cae la matricula, no el ingreso"
    return "Sin tendencia sostenida"


def main():
    con = duckdb.connect(str(DUCKDB))

    # Se parte de dim_programa para cubrir TODOS los programas: los que no
    # tienen datos en la ventana quedan como 'Serie insuficiente' en vez de
    # faltar, y la relacion 1:1 con dim_programa queda completa.
    prog = con.execute(
        "SELECT programa_sk, nombre_grupo_3 AS campo FROM dim_programa").df()

    for sufijo, (hecho, medida, semestre) in SERIES.items():
        sql = dict(hecho=hecho, medida=medida, semestre=semestre, ucsp=UCSP)
        p = tendencias(con.execute(POR_PROGRAMA.format(**sql)).df())
        c = tendencias(con.execute(POR_CAMPO_SUR.format(**sql)).df())
        print(f"{hecho}: {len(p):,} programas y {len(c)} campos CINE del sur evaluados")

        p = p.rename(columns={"llave": "programa_sk", "anios": f"anios_{sufijo}",
                              "cagr": f"cagr_{sufijo}", "p_valor": f"p_valor_{sufijo}",
                              "tendencia": f"tendencia_{sufijo}",
                              "ultimo_anio": f"{medida}_ultimo_anio"})
        c = c[["llave", "cagr"]].rename(columns={"llave": "campo",
                                                 "cagr": f"cagr_campo_sur_{sufijo}"})
        prog = prog.merge(p, on="programa_sk", how="left").merge(c, on="campo", how="left")

        prog[f"anios_{sufijo}"] = prog[f"anios_{sufijo}"].fillna(0).astype(int)
        prog[f"{medida}_ultimo_anio"] = prog[f"{medida}_ultimo_anio"].fillna(0).astype(int)
        prog[f"tendencia_{sufijo}"] = prog[f"tendencia_{sufijo}"].fillna("Serie insuficiente")
        prog[f"delta_campo_sur_{sufijo}"] = (prog[f"cagr_{sufijo}"]
                                             - prog[f"cagr_campo_sur_{sufijo}"])
        prog[f"cuadrante_{sufijo}"] = [
            cuadrante(a, b) for a, b in zip(prog[f"cagr_{sufijo}"],
                                            prog[f"cagr_campo_sur_{sufijo}"])]

    prog["lectura"] = [lectura(i, m) for i, m in
                       zip(prog["tendencia_ing"], prog["tendencia_mat"])]
    prog = prog.drop(columns=["campo"])

    con.execute("CREATE OR REPLACE TABLE dim_tendencia_programa AS "
                "SELECT * FROM prog ORDER BY programa_sk")
    con.execute(f"COPY dim_tendencia_programa TO "
                f"'{(GOLD / 'dim_tendencia_programa.parquet').as_posix()}' (FORMAT parquet)")
    con.close()

    print(f"\n{len(prog):,} programas. Tendencia por serie:")
    resumen = pd.concat([prog["tendencia_ing"].value_counts().rename("ingresantes"),
                         prog["tendencia_mat"].value_counts().rename("matricula")], axis=1)
    print(resumen.fillna(0).astype(int).to_string())
    print("\nLectura cruzada de las dos series:")
    print(prog["lectura"].value_counts().to_string())
    print(f"\nGuardado en {GOLD / 'dim_tendencia_programa.parquet'}")


if __name__ == "__main__":
    main()
