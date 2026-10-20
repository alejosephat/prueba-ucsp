"""Constantes del proyecto. Todo lo configurable vive aqui."""
from pathlib import Path

RAIZ = Path(__file__).parent
BRONZE = RAIZ / "data" / "bronze"
TMP = RAIZ / "data" / "tmp"
GOLD = RAIZ / "data" / "gold"
SQL = RAIZ / "sql"
SALIDAS = RAIZ / "salidas"
REFERENCIAS = RAIZ / "referencias"
DOCS = RAIZ / "docs"
POWERBI = RAIZ / "powerbi"
DUCKDB = RAIZ / "data" / "sunedu.duckdb"

API = "https://portalapi.tuni.pe/api"
SHAREPOINT = "https://sunedu.sharepoint.com"

# ---------------------------------------------------------------- alcance
# Se ingesta el catalogo COMPLETO de TUNI: 56 archivos, 1 270 MB de zips.
# No se recorta en la ingesta. El recorte, si hace falta, se decide en gold
# y queda documentado ahi.
#
# Por que no recortar: bronze es la foto de lo que SUNEDU publico. Si manana
# una pregunta necesita 2020 o el semestre II, el dato ya esta bajado y con
# su sha256; no hay que volver a la fuente. El costo de bajarlo todo es
# 1,2 GB una sola vez; el costo de no bajarlo es re-ingestar.
ANIOS = [2020, 2021, 2022, 2023, 2024, 2025]
SEMESTRES = ["I", "II"]

# Periodos publicados por categoria, verificados contra el catalogo.
PERIODOS = {
    "Ingresante":           [str(a) for a in ANIOS],
    "Matriculado":          [f"{a}-{s}" for a in ANIOS for s in SEMESTRES],
    "Docente":              [f"{a}-{s}" for a in ANIOS for s in SEMESTRES],
    "Postulante":           [str(a) for a in ANIOS if a >= 2022],
    "Egresado":             [str(a) for a in ANIOS if a >= 2022],
    "Carnés Universitarios": [str(a) for a in ANIOS if a >= 2021],
    "GYT Nacionales":       [str(a) for a in ANIOS],
    "GYT Extranjeros":      [str(a) for a in ANIOS],
    "Oferta universitaria": ["Sin Periodo"],
}
ARCHIVOS = [(c, p) for c, ps in PERIODOS.items() for p in ps]

# ------------------------------------------------- ventana de analisis
# 2020 se ingesta pero NO entra en la regresion de tendencia: fue el anio de
# ruptura por la pandemia (congelamientos masivos). Entra como linea base para
# medir el choque, no como punto de la serie. Ver decision B1.
ANIOS_TENDENCIA = [2021, 2022, 2023, 2024, 2025]

# Semestre de referencia para la serie anual comparable de matricula.
# Con los 12 semestres bajados esto ya NO es un recorte de datos: es el
# filtro de UNA medida, y el semestre II sigue disponible en el modelo.
SEMESTRE_SERIE_ANUAL = 1

UCSP = "260000062"  # Universidad Catolica San Pablo
NIVEL_PREGRADO = "Carrera Profesional"

# Umbral de matricula para entrar al ranking bottom-5 (si no, lo copan
# programas que abrieron ese anio con 2 alumnos).
UMBRAL_BOTTOM = 10

# Criterios de "tendencia sostenida" (ver 04_tendencias.py)
MIN_ANIOS_TENDENCIA = 4
P_VALOR_MAX = 0.05
CAGR_MIN = 0.03
