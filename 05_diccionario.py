"""Genera docs/diccionario_datos.md (entregable 5.3).

La estructura (tablas, columnas, tipos, conteos) se lee de la base construida,
no se escribe a mano: asi el diccionario no puede describir columnas que no
existan ni quedarse desactualizado cuando cambie el modelo. Solo la prosa de
cada campo esta redactada.
"""
import duckdb

from config import DOCS, DUCKDB

GRANO = {
    "dim_periodo": "Una fila por anio. Dimension conformada: se relaciona con los SEIS hechos. "
                   "El grano es anual porque es el grano comun a todos; el eje semestral vive en dim_semestre.",
    "dim_semestre": "Una fila por periodo lectivo: I, II y 'Otro'. Conformada solo sobre los tres hechos "
                    "semestrales (matricula, egresados, docentes). La fila 'Otro' recoge los periodos de "
                    "egreso extraordinarios que trae la fuente de egresados.",
    "dim_universidad": "Una fila por universidad (codigo INEI).",
    "dim_programa": "Una fila por programa de una universidad.",
    "dim_ubicacion": "Una fila por combinacion departamento + provincia.",
    "dim_tendencia_programa": "Una fila por programa. Salida del componente estadistico (04_tendencias.py).",
    "fct_ingresantes": "Una fila por anio x universidad x programa x ubicacion.",
    "fct_matricula": "Una fila por anio x SEMESTRE x universidad x programa x ubicacion. Estan los 12 "
                     "semestres de 2020-I a 2025-II; la serie anual comparable se obtiene filtrando "
                     "dim_semestre[es_serie_anual], que es un filtro de consulta y no un recorte de datos.",
    "fct_postulantes": "Una fila por anio x universidad x programa (primera opcion) x ubicacion.",
    "fct_egresados": "Una fila por anio x semestre x universidad x programa. NO tiene ubicacion: medido, "
                     "DEPARTAMENTO_FILIAL viene vacio en el 100 % de las 587 527 filas de la fuente.",
    "fct_docentes": "Una fila por anio x semestre x universidad. Grano mas grueso que los demas hechos y "
                    "declarado: la fuente de docentes no trae programa, y su unica geografia es el "
                    "departamento de NACIMIENTO del docente, no el del local donde ensena.",
    "fct_titulos": "Una fila por anio de resolucion x universidad. La universidad se resuelve por igualdad "
                   "de nombre normalizado porque la fuente no trae codigo INEI (ver control de calidad #11).",
}

LLAVE = {
    "dim_periodo": "anio",
    "dim_universidad": "codigo_inei",
    "dim_programa": "programa_sk  (compuesta: codigo_inei + codigo_siu_programa)",
    "dim_ubicacion": "ubicacion_sk  (compuesta: departamento + provincia)",
    "dim_tendencia_programa": "programa_sk",
    "fct_ingresantes": "anio + programa_sk + ubicacion_sk",
    "fct_matricula": "anio + semestre + programa_sk + ubicacion_sk",
    "fct_postulantes": "anio + programa_sk + ubicacion_sk",
    "dim_semestre": "semestre",
    "fct_egresados": "anio + semestre + programa_sk",
    "fct_docentes": "anio + semestre + codigo_inei",
    "fct_titulos": "anio + codigo_inei",
}

CAMPO = {
    "anio": "Anio del periodo academico. FK a dim_periodo.",
    "etiqueta": "Anio como texto, para etiquetar visuales.",
    "orden": "Posicion del anio en la serie, para ordenar ejes.",
    "es_ultimo_anio": "Marca el ultimo anio disponible, para tarjetas de resumen.",
    "es_tendencia": "Marca los anios que entran en la regresion de tendencia (2021-2025). 2020 esta "
                    "ingestado y visible, pero fuera del test: fue el anio de ruptura por la pandemia "
                    "(ver el control de calidad #14, que mide cuanto se desvia).",
    "semestre": "Periodo lectivo dentro del anio: 1, 2, o 0 para los periodos extraordinarios. "
                "FK a dim_semestre.",
    "es_serie_anual": "Marca el semestre que define la serie anual comparable. Las medidas de matricula y "
                      "de docentes filtran por este atributo en vez de por un literal, para que no haya "
                      "dos verdades entre config.py y el modelo.",
    "codigo_inei": "Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad.",
    "nombre_universidad": "Nombre de la universidad, resuelto al valor mas reciente no nulo.",
    "tipo_entidad": "Universidad, Escuela de Posgrado, Escuela Superior o Instituto.",
    "tipo_gestion": "Publico o Privado. **Filtro obligatorio** del enunciado.",
    "tipo_constitucion": "Publica, Privada asociativa o Privada societaria.",
    "licenciamiento": "Estado de licenciamiento institucional ante SUNEDU.",
    "es_ucsp": "Marca la Universidad Catolica San Pablo (codigo INEI 260000062).",
    "departamento_sede": "Departamento donde la universidad concentra MAS matricula. Define su sede principal.",
    "macrorregion_sede": "Macrorregion de la sede principal. Clasifica a la universidad entera.",
    "es_macrosur_sede": "Marca las universidades con sede principal en el sur. **Distinto de "
                        "dim_ubicacion[es_macrosur]**, que marca donde se imparte un programa: una universidad "
                        "de Lima con filial en Cusco aporta matricula al sur pero no es una universidad del sur.",
    "programa_sk": "Llave sustituta: md5(codigo_inei + '-' + codigo_siu_programa). Es compuesta porque "
                   "codigo_siu_programa NO es unico a nivel nacional (288 de 471 codigos se repiten).",
    "codigo_siu_programa": "Codigo del programa en el SIU. Unico solo dentro de cada universidad.",
    "nombre_programa": "Nombre del programa segun la universidad, al valor mas reciente no nulo.",
    "nombre_programa_std": "Nombre normalizado (mayusculas, sin tildes, espacios colapsados).",
    "codigo_grupo_1": "Codigo del campo amplio CINE-UNESCO (11 categorias).",
    "nombre_grupo_1": "Campo amplio de estudio CINE-UNESCO.",
    "codigo_grupo_3": "Codigo del campo detallado CINE-UNESCO (83 categorias).",
    "nombre_grupo_3": "Campo detallado CINE-UNESCO. **Criterio de homologacion** entre universidades.",
    "campo_estudio": "nombre_grupo_3, o 'Sin clasificar CINE' cuando la fuente no lo reporta. "
                     "Usar este campo en los visuales para que los no clasificados sigan siendo visibles.",
    "nivel_academico": "Nivel del programa. El modelo contiene solo 'Carrera Profesional' (pregrado).",
    "ubicacion_sk": "Llave sustituta de la ubicacion. FK a dim_ubicacion.",
    "departamento": "Departamento del local o filial donde se dicta el programa. **Filtro obligatorio**.",
    "provincia": "Provincia del local o filial.",
    "macrorregion": "Norte, Centro, Sur u Oriente. Definido en referencias/macrorregiones.csv.",
    "es_macrosur": "Marca la macrorregion sur. **Filtro obligatorio** del enunciado.",
    "ingresantes": "Personas distintas que ingresan al programa ese anio.",
    "egresados": "Personas distintas que egresan (terminan los cursos) del programa en el periodo. "
                 "Egresar es un FLUJO, asi que sumar los dos semestres de un anio es correcto -- a "
                 "diferencia de la matricula, que es un stock y se duplicaria.",
    "nota_promedio": "Nota promedio de los egresados del grupo. Al agregarla hay que reponderarla por "
                     "numero de egresados: promediar promedios de grupos de distinto tamano da un numero "
                     "que no corresponde a ningun alumno.",
    "creditos_aprobados": "Creditos aprobados al egresar, promedio del grupo.",
    "docentes": "Docentes distintos de pregrado en la universidad y el semestre. La fuente repite al "
                "docente una vez por cada grado que acredita, de ahi el conteo de personas distintas.",
    "docentes_tiempo_completo": "Docentes a tiempo completo o dedicacion exclusiva. Insumo del porcentaje "
                                "que SUNEDU exige como Condicion Basica de Calidad.",
    "docentes_posgrado": "Docentes con grado de maestro o doctor.",
    "docentes_ordinarios": "Docentes en condicion de ordinarios (de carrera), frente a contratados.",
    "titulos": "EVENTOS de titulacion con resolucion en el anio: grados de bachiller y titulos "
               "profesionales. Titulacion EFECTIVA (obtener el diploma), que no es lo mismo que egreso "
               "(terminar los cursos). NO es un conteo de personas: medido, 437 872 personas tienen dos "
               "titulos (el grado y el titulo) y 4 153 tienen tres o mas.",
    "personas": "Personas distintas tituladas en el anio. Es la cifra comparable con un conteo de "
                "egresados; `titulos` no lo es, porque cuenta eventos.",
    "bachilleres": "De los anteriores, los que son grado de bachiller.",
    "titulados": "De los anteriores, los que son titulo profesional.",
    "anios_estudio_mediana": "Mediana de anios entre matricula y egreso, calculada sobre las fechas que "
                             "trae la propia fuente de grados y titulos. Mide duracion real de estudios.",
    "matriculados": "Personas distintas matriculadas en el programa en el periodo I del anio.",
    "postulaciones": "Postulaciones recibidas. Una persona puede postular a varios programas.",
    "postulantes": "Personas distintas que postulan al programa como primera opcion.",
    "admitidos": "Postulaciones con ES_INGRESANTE = SI en la fuente. Numerador de la tasa de admision.",
    "anios_ing": "Anios con ingresantes positiva en 2021-2025 que entran en la regresion.",
    "cagr_ing": "CAGR de ingresantes estimado por OLS sobre log(ingresantes) 2021-2025.",
    "p_valor_ing": "p-valor del t-test de la pendiente de ingresantes (gl = n - 2).",
    "tendencia_ing": "Crecimiento sostenido / Caida sostenida / Sin tendencia sostenida / Serie insuficiente.",
    "ingresantes_ultimo_anio": "Ingresantes del ultimo anio de la ventana, para dimensionar el programa.",
    "cagr_campo_sur_ing": "CAGR OLS de ingresantes del mismo campo CINE en la macrorregion sur, SIN la UCSP.",
    "delta_campo_sur_ing": "cagr_ing menos cagr_campo_sur_ing. Positivo = el programa gana cuota en el sur.",
    "cuadrante_ing": "Posicion de ingresantes frente a su campo en el sur: gana/pierde cuota, crece o cae con el campo.",
    "anios_mat": "Anios con matricula positiva en 2021-2025 que entran en la regresion.",
    "cagr_mat": "CAGR de matricula estimado por OLS sobre log(matriculados) 2021-2025.",
    "p_valor_mat": "p-valor del t-test de la pendiente de matricula (gl = n - 2).",
    "tendencia_mat": "Crecimiento sostenido / Caida sostenida / Sin tendencia sostenida / Serie insuficiente.",
    "matriculados_ultimo_anio": "Matriculados del ultimo anio de la ventana, para dimensionar el programa.",
    "cagr_campo_sur_mat": "CAGR OLS de matricula del mismo campo CINE en la macrorregion sur, SIN la UCSP.",
    "delta_campo_sur_mat": "cagr_mat menos cagr_campo_sur_mat. Positivo = el programa gana cuota en el sur.",
    "cuadrante_mat": "Posicion de matricula frente a su campo en el sur: gana/pierde cuota, crece o cae con el campo.",
    "lectura": "Cruce de las dos series: crecimiento o caida confirmada, alerta (cae el ingreso y la matricula aun no), o la matricula se mueve sin el ingreso.",
}

CABECERA = """# Diccionario de datos

Modelo en **esquema estrella**. La estructura de este documento se lee directamente
de la base construida (`data/sunedu.duckdb`) al ejecutar `05_diccionario.py`, de modo
que no puede describir columnas que no existan.

- **Fuente:** datos abiertos de SUNEDU publicados en <https://tuni.pe/datos>
- **Recorte:** ingresantes y matriculados 2021-2025; postulantes 2022-2025
- **Alcance:** solo pregrado (`NIVEL_ACADEMICO = 'Carrera Profesional'`)
- **Decisiones de modelado y su sustento:** `docs/decisiones_tecnicas.md`

## Relaciones del modelo

Las cuatro dimensiones son **conformadas**: filtran los tres hechos a la vez.
Todas las relaciones son uno a muchos, de la dimension al hecho, en **direccion
simple**.

```
                        dim_periodo (anio)
                               |
      dim_universidad ---------+--------- dim_ubicacion
       (codigo_inei)           |          (ubicacion_sk)
                               |
            fct_ingresantes / fct_matricula / fct_postulantes
                               |
                        dim_programa (programa_sk)
                               |
                   dim_tendencia_programa (1:1)
```

> `dim_programa` contiene `codigo_inei` como **atributo descriptivo**, no como
> llave foranea: no debe crearse una relacion entre `dim_programa` y
> `dim_universidad`, porque generaria una ruta de filtrado ambigua con la que ya
> existe desde los hechos.

## Resumen de tablas

"""


def generar(con):
    tablas = [t[0] for t in con.execute(
        "SELECT table_name FROM duckdb_tables() "
        "WHERE table_name LIKE 'dim%' OR table_name LIKE 'fct%' ORDER BY 1").fetchall()]

    lineas = [CABECERA, "| Tabla | Tipo | Filas | Granularidad |", "|---|---|---|---|"]
    for t in tablas:
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        tipo = "Hecho" if t.startswith("fct") else "Dimension"
        lineas.append(f"| `{t}` | {tipo} | {n:,} | {GRANO.get(t, '')} |")

    for t in tablas:
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        cols = con.execute("SELECT column_name, data_type FROM duckdb_columns() "
                           f"WHERE table_name = '{t}' ORDER BY column_index").fetchall()
        lineas += ["", f"## `{t}`", "",
                   f"**Granularidad:** {GRANO.get(t, 'n/d')}", "",
                   f"**Llave:** `{LLAVE.get(t, 'n/d')}`", "",
                   f"**Filas:** {n:,}", "",
                   "| Columna | Tipo | Descripcion |", "|---|---|---|"]
        lineas += [f"| `{c}` | {ti} | {CAMPO.get(c, '')} |" for c, ti in cols]

    return "\n".join(lineas) + "\n"


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB), read_only=True)
    destino = DOCS / "diccionario_datos.md"
    destino.write_text(generar(con), encoding="utf-8")
    n_tablas = len(con.execute(
        "SELECT table_name FROM duckdb_tables() "
        "WHERE table_name LIKE 'dim%' OR table_name LIKE 'fct%'").fetchall())
    con.close()
    print(f"{n_tablas} tablas documentadas en {destino}")


if __name__ == "__main__":
    main()
