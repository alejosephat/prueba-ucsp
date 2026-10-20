"""Genera los artefactos de Power BI a partir de una unica definicion de medidas.

Salidas:
  powerbi/medidas.csx        script de Tabular Editor: crea todas las medidas
  powerbi/medidas.dax        las mismas formulas en texto plano (respaldo)
  docs/catalogo_medidas.md   catalogo documentado (entregable 5.3)

Una sola fuente (la lista MEDIDAS de abajo) para que el catalogo nunca quede
desincronizado del modelo.

Convenciones DAX aplicadas:
  - Todas las medidas son explicitas; ninguna agregacion implicita en los visuales.
  - VAR para separar calculo de presentacion y evaluar cada cosa una sola vez.
  - DIVIDE() en todo cociente: devuelve BLANK en vez de error al dividir entre cero.
  - REMOVEFILTERS() explicito en vez de ALL() para que la intencion se lea sola.
  - dim_periodo[anio] es un entero, no una fecha, asi que no se usan funciones de
    time intelligence: el desplazamiento interanual es explicito (anio - 1).
"""
from config import DOCS, POWERBI, UMBRAL_BOTTOM

# (nombre, carpeta, formato, descripcion de negocio, expresion DAX)
MEDIDAS = [
    # ---------------------------------------------------------------- base
    ("Ingresantes", "01 Base", "#,0",
     "Personas distintas que ingresan a un programa de pregrado en el anio.",
     "SUM ( fct_ingresantes[ingresantes] )"),

    ("Matriculados", "01 Base", "#,0",
     "Personas distintas matriculadas en pregrado en la serie anual comparable "
     "(un semestre fijo por anio). Es un stock: con varios anios en contexto "
     "devuelve el del ULTIMO anio, no la suma. El slicer de semestre no la "
     "afecta: para eso esta [Matriculados Semestre].",
     """-- La matricula es un STOCK: la misma persona aparece en cada semestre y en
-- cada anio que sigue estudiando. Por eso esta medida no es un SUM, en dos ejes:
--
--   Semestre. fct_matricula trae los 12 semestres de 2020-I a 2025-II. Se fija
--   el marcado en dim_semestre[es_serie_anual]: sumar I y II contaria dos veces
--   a quien estudio todo el anio. El REMOVEFILTERS hace falta ademas del
--   filtro, para que una seleccion del slicer de semestre no se intersecte.
--
--   Anio. Con varios anios en contexto (una tarjeta sin filtro de periodo, la
--   fila de total de una tabla) devuelve el ULTIMO anio con dato: sumar
--   2021-2025 contaria a la misma persona hasta cinco veces.
VAR UltimoAnio =
    CALCULATE (
        MAX ( fct_matricula[anio] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[es_serie_anual] = TRUE
    )
RETURN
    CALCULATE (
        SUM ( fct_matricula[matriculados] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[es_serie_anual] = TRUE,
        dim_periodo[anio] = UltimoAnio
    )"""),

    ("Ingresantes Ultimo Anio", "01 Base", "#,0",
     "Ingresantes del ULTIMO anio del contexto. [Ingresantes] es un flujo y suma "
     "el rango, que es lo correcto en una serie; esta es la cifra de la ficha.",
     """VAR UltimoAnio = MAX ( fct_ingresantes[anio] )
RETURN
    CALCULATE ( [Ingresantes], dim_periodo[anio] = UltimoAnio )"""),

    ("Postulaciones", "01 Base", "#,0",
     "Postulaciones recibidas (una persona puede postular a varios programas).",
     "SUM ( fct_postulantes[postulaciones] )"),

    ("Postulantes", "01 Base", "#,0",
     "Personas distintas que postulan. Menor que Postulaciones por multipostulacion.",
     "SUM ( fct_postulantes[postulantes] )"),

    ("Admitidos", "01 Base", "#,0",
     "Postulaciones que resultaron en ingreso, segun la propia fuente de postulantes.",
     "SUM ( fct_postulantes[admitidos] )"),

    ("Programas Activos", "01 Base", "#,0",
     "Programas con matricula mayor a cero en el ULTIMO anio del contexto.",
     """-- El filtro de semestre va por la misma razon que en [Matriculados]. Y es un
-- stock: con varios anios en contexto cuenta los programas activos del ultimo
-- anio, no los que tuvieron matricula en algun anio del rango. Medido: sin
-- esta regla, la tarjeta nacional decia 2 680 programas en 2021-2025.
VAR UltimoAnio =
    CALCULATE (
        MAX ( fct_matricula[anio] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[es_serie_anual] = TRUE
    )
RETURN
    CALCULATE (
        DISTINCTCOUNT ( fct_matricula[programa_sk] ),
        fct_matricula[matriculados] > 0,
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[es_serie_anual] = TRUE,
        dim_periodo[anio] = UltimoAnio
    )"""),

    # -------------------------------------------------- variacion interanual
    ("Matriculados AA", "02 Variacion interanual", "#,0",
     "Matriculados del anio anterior. BLANK si el anio previo no esta en la serie.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
RETURN
    CALCULATE (
        [Matriculados],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioActual - 1
    )"""),

    ("Var. Matricula (abs)", "02 Variacion interanual", "+#,0;-#,0;0",
     "Diferencia absoluta de matriculados contra el anio anterior. Con varios anios "
     "en contexto, la del ultimo.",
     """-- Las dos puntas se fijan a un anio concreto. Con varios anios en contexto
-- (la fila de total) la medida devuelve la variacion del ULTIMO anio contra
-- el anterior. Sin fijar la punta actual, en [Ingresantes] -que es un flujo y
-- si se suma- la fila de total compararia todo el rango contra un solo anio.
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior = [Matriculados AA]
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), Actual - Anterior )"""),

    ("Var. Matricula (%)", "02 Variacion interanual", "+0.0%;-0.0%;0.0%",
     "Variacion porcentual de matriculados contra el anio anterior. Con varios anios "
     "en contexto, la del ultimo.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior = [Matriculados AA]
RETURN
    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )"""),

    ("Ingresantes AA", "02 Variacion interanual", "#,0",
     "Ingresantes del anio anterior.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
RETURN
    CALCULATE (
        [Ingresantes],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioActual - 1
    )"""),

    ("Var. Ingresantes (abs)", "02 Variacion interanual", "+#,0;-#,0;0",
     "Diferencia absoluta de ingresantes contra el anio anterior. Con varios anios "
     "en contexto, la del ultimo.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior = [Ingresantes AA]
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), Actual - Anterior )"""),

    ("Var. Ingresantes (%)", "02 Variacion interanual", "+0.0%;-0.0%;0.0%",
     "Variacion porcentual de ingresantes contra el anio anterior. Con varios anios "
     "en contexto, la del ultimo.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior = [Ingresantes AA]
RETURN
    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )"""),

    ("Var. Cuota del Sur (pp)", "02 Variacion interanual", '+0.00" pp";-0.00" pp";0.00" pp"',
     "Cambio de la cuota de la matricula del sur contra el anio anterior, en puntos porcentuales.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Cuota de Mercado en el Sur], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [Cuota de Mercado en el Sur], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) * 100 )"""),

    ("Var. Programas Activos", "02 Variacion interanual", '+0;-0;0',
     "Programas activos del ultimo anio menos los del anio anterior.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Programas Activos], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [Programas Activos], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) )"""),

    ("Var. HHI", "02 Variacion interanual", '+#,0;-#,0;0',
     "Cambio del HHI contra el anio anterior. Negativo = la matricula se diversifica.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [HHI Universidad], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [HHI Universidad], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) )"""),

    ("Var. Tasa de Admision UCSP (pp)", "02 Variacion interanual", '+0.0" pp";-0.0" pp";0.0" pp"',
     "Cambio de la tasa de admision de la UCSP contra el anio anterior, en puntos porcentuales.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Tasa de Admision UCSP], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [Tasa de Admision UCSP], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) * 100 )"""),

    ("Var. Postulaciones (%)", "02 Variacion interanual", "+0.0%;-0.0%;0.0%",
     "Variacion porcentual de las postulaciones contra el anio anterior.",
     """VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Postulaciones], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [Postulaciones], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )"""),

    # ------------------------------------------------------- participacion
    ("% Participacion en su Universidad", "03 Participacion", "0.0%",
     "Peso del programa dentro de la matricula de SU universidad. El denominador "
     "quita el filtro de programa pero reimpone la universidad a la que pertenece "
     "el programa del contexto, para que no se escape al total nacional.",
     """VAR MatriculaPrograma = [Matriculados]
-- La universidad del programa en contexto, capturada ANTES de quitar el filtro.
-- dim_programa[codigo_inei] es atributo descriptivo, no llave foranea, asi que
-- se traslada a dim_universidad con TREATAS. Sin esto, REMOVEFILTERS por si solo
-- dejaria el denominador en el total nacional cuando no hay universidad filtrada.
VAR SuUniversidad = VALUES ( dim_programa[codigo_inei] )
VAR MatriculaUniversidad =
    CALCULATE (
        [Matriculados],
        REMOVEFILTERS ( dim_programa ),
        TREATAS ( SuUniversidad, dim_universidad[codigo_inei] )
    )
RETURN
    DIVIDE ( MatriculaPrograma, MatriculaUniversidad )"""),

    # ------------------------------------------------------------- ranking
    ("Ranking Programa", "04 Ranking", "#,0",
     "Posicion del programa por matricula. ALLSELECTED (no ALL) hace que el "
     "ranking se recalcule dentro de los filtros activos de universidad, "
     "departamento, gestion y periodo.",
     """IF (
    NOT ISBLANK ( [Matriculados] ),
    RANKX (
        ALLSELECTED ( dim_programa[nombre_programa] ),
        [Matriculados],
        ,
        DESC,
        DENSE
    )
)"""),

    ("Ranking Programa (Ingresantes)", "04 Ranking", "#,0",
     "Posicion del programa por ingresantes, tambien sensible a los filtros.",
     """IF (
    NOT ISBLANK ( [Ingresantes] ),
    RANKX (
        ALLSELECTED ( dim_programa[nombre_programa] ),
        [Ingresantes],
        ,
        DESC,
        DENSE
    )
)"""),

    ("Ranking Programa Inverso", "04 Ranking", "#,0",
     "Posicion desde la cola, para el bottom-5. Excluye programas por debajo del "
     "umbral minimo: sin eso el fondo lo ocupan programas que abrieron ese anio "
     "con 2 o 3 alumnos y el visual deja de ser informativo.",
     f"""VAR Umbral = {UMBRAL_BOTTOM}
RETURN
    IF (
        [Matriculados] >= Umbral,
        RANKX (
            FILTER ( ALLSELECTED ( dim_programa[nombre_programa] ), [Matriculados] >= Umbral ),
            [Matriculados],
            ,
            ASC,
            DENSE
        )
    )"""),

    ("Ranking Programa Inverso (Ingresantes)", "04 Ranking", "#,0",
     "Posicion desde la cola por ingresantes, para el bottom-5 de ingreso. Mismo "
     "umbral minimo que [Ranking Programa Inverso].",
     f"""VAR Umbral = {UMBRAL_BOTTOM}
RETURN
    IF (
        [Ingresantes] >= Umbral,
        RANKX (
            FILTER ( ALLSELECTED ( dim_programa[nombre_programa] ), [Ingresantes] >= Umbral ),
            [Ingresantes],
            ,
            ASC,
            DENSE
        )
    )"""),

    # ----------------------------------------------------- crecimiento
    ("CAGR Matricula", "05 Crecimiento", "+0.0%;-0.0%;0.0%",
     "Tasa de crecimiento anual compuesta de la matricula entre el primer y el "
     "ultimo anio seleccionados. BLANK si hay un solo anio o si el inicio es cero.",
     """VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )
VAR AnioIni = MINX ( AniosVisibles, dim_periodo[anio] )
VAR AnioFin = MAXX ( AniosVisibles, dim_periodo[anio] )
VAR Saltos = AnioFin - AnioIni
VAR ValorIni =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioIni )
VAR ValorFin =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioFin )
RETURN
    IF (
        Saltos > 0 && ValorIni > 0 && ValorFin > 0,
        ( ValorFin / ValorIni ) ^ DIVIDE ( 1, Saltos ) - 1
    )"""),

    ("CAGR Ingresantes", "05 Crecimiento", "+0.0%;-0.0%;0.0%",
     "Tasa de crecimiento anual compuesta de los ingresantes del rango seleccionado.",
     """VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )
VAR AnioIni = MINX ( AniosVisibles, dim_periodo[anio] )
VAR AnioFin = MAXX ( AniosVisibles, dim_periodo[anio] )
VAR Saltos = AnioFin - AnioIni
VAR ValorIni =
    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioIni )
VAR ValorFin =
    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioFin )
RETURN
    IF (
        Saltos > 0 && ValorIni > 0 && ValorFin > 0,
        ( ValorFin / ValorIni ) ^ DIVIDE ( 1, Saltos ) - 1
    )"""),

    ("Crecimiento Acumulado %", "05 Crecimiento", "+0.0%;-0.0%;0.0%",
     "Variacion total de la matricula entre el primer y el ultimo anio seleccionados.",
     """VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )
VAR AnioIni = MINX ( AniosVisibles, dim_periodo[anio] )
VAR AnioFin = MAXX ( AniosVisibles, dim_periodo[anio] )
VAR ValorIni =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioIni )
VAR ValorFin =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioFin )
RETURN
    DIVIDE ( ValorFin - ValorIni, ValorIni )"""),

    # ------------------------------------------------------------ benchmark
    ("Matricula UCSP", "06 Benchmark", "#,0",
     "Serie de referencia: matricula de la UCSP. Como todos los comparadores, "
     "ignora la universidad y la ubicacion (lo que define la cohorte) y respeta "
     "periodo, programa y gestion, que es lo que hace comparables las series.",
     """-- ALLEXCEPT y no REMOVEFILTERS ( dim_universidad ): el comparador debe
-- respetar la gestion. Medido en 2025, la UCSP admite el 56 % de las
-- postulaciones; el resto del sur, el 34 %; las privadas del sur, el 77 %.
-- Contra el sur completo -arrastrado por las publicas, que admiten 13-15 %-
-- la UCSP parece menos selectiva; contra sus pares privados lo es mas. Un
-- comparador que ignora la gestion invierte la conclusion, y la gestion es
-- ademas un filtro obligatorio del enunciado.
CALCULATE (
    [Matriculados],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)"""),

    ("Matricula Macrosur", "06 Benchmark", "#,0",
     "Matricula IMPARTIDA en locales de la macrorregion sur, sea cual sea la sede "
     "de la universidad. Es un concepto distinto de es_macrosur_sede, que clasifica "
     "a la universidad entera: una universidad de Lima con filial en Cusco aporta "
     "a esta medida, pero no cuenta como universidad del sur.",
     """CALCULATE (
    [Matriculados],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE
)"""),

    ("Matricula Nacional", "06 Benchmark", "#,0",
     "Serie de referencia: matricula nacional. Ignora universidad y ubicacion "
     "y respeta periodo, programa y gestion, igual que las otras dos series del "
     "grupo, para que las tres sean comparables.",
     """CALCULATE (
    [Matriculados],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion )
)"""),

    ("Indice Matricula UCSP", "06 Benchmark", "#,0.0",
     "Matricula de la UCSP en base 100 del primer anio seleccionado. La "
     "indexacion es lo que hace comparables tres series de escalas muy distintas "
     "(UCSP ~8 mil, sur ~200 mil, nacional ~1.6 millones) en un mismo grafico.",
     """VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Matricula UCSP]
VAR Base =
    CALCULATE (
        [Matricula UCSP],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100"""),

    ("Indice Matricula Macrosur", "06 Benchmark", "#,0.0",
     "Matricula de la macrorregion sur en base 100 del primer anio seleccionado.",
     """VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Matricula Macrosur]
VAR Base =
    CALCULATE (
        [Matricula Macrosur],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100"""),

    ("Indice Matricula Nacional", "06 Benchmark", "#,0.0",
     "Matricula nacional en base 100 del primer anio seleccionado.",
     """VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Matricula Nacional]
VAR Base =
    CALCULATE (
        [Matricula Nacional],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100"""),

    # Las tarjetas de la pregunta 4.1. Reusan [CAGR Matricula] y [CAGR
    # Ingresantes] con la misma simetria que [Matricula UCSP]: quitan los filtros
    # que definen la cohorte (universidad y ubicacion) y respetan periodo y
    # programa. Asi las tres cifras se comparan entre si aunque el usuario mueva
    # los segmentadores, sin depender de filtros a nivel de visual.
    ("CAGR Matricula UCSP", "06 Benchmark", "+0.0%;-0.0%;0.0%",
     "CAGR de la matricula de la UCSP en el rango de anios seleccionado.",
     """CALCULATE (
    [CAGR Matricula],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)"""),

    ("CAGR Matricula Macrosur", "06 Benchmark", "+0.0%;-0.0%;0.0%",
     "CAGR de la matricula de programas impartidos en la macrorregion sur en el rango "
     "de anios seleccionado.",
     """CALCULATE (
    [CAGR Matricula],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE
)"""),

    ("CAGR Matricula Nacional", "06 Benchmark", "+0.0%;-0.0%;0.0%",
     "CAGR de la matricula del pais en el rango de anios seleccionado.",
     """CALCULATE (
    [CAGR Matricula],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion )
)"""),

    ("CAGR Ingresantes UCSP", "06 Benchmark", "+0.0%;-0.0%;0.0%",
     "CAGR de los ingresantes de la UCSP en el rango de anios seleccionado.",
     """CALCULATE (
    [CAGR Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)"""),

    ("CAGR Ingresantes Macrosur", "06 Benchmark", "+0.0%;-0.0%;0.0%",
     "CAGR de los ingresantes de programas impartidos en la macrorregion sur en el rango "
     "de anios seleccionado.",
     """CALCULATE (
    [CAGR Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE
)"""),

    ("CAGR Ingresantes Nacional", "06 Benchmark", "+0.0%;-0.0%;0.0%",
     "CAGR de los ingresantes del pais en el rango de anios seleccionado.",
     """CALCULATE (
    [CAGR Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion )
)"""),

    # Contraparte de las series de matricula para el ingreso, que es donde esta
    # el hallazgo de la pregunta 4.1: el ingreso de la UCSP cae mientras el del
    # sur crece. Misma simetria de filtros que [Matricula UCSP].
    ("Ingresantes UCSP", "06 Benchmark", "#,0",
     "Serie de referencia: ingresantes de la UCSP. Ignora universidad y ubicacion; "
     "respeta periodo, programa y gestion.",
     """CALCULATE (
    [Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)"""),

    ("Ingresantes Macrosur", "06 Benchmark", "#,0",
     "Serie de referencia: ingresantes de programas impartidos en la macrorregion sur. Ignora universidad y ubicacion; "
     "respeta periodo, programa y gestion.",
     """CALCULATE (
    [Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE
)"""),

    ("Ingresantes Nacional", "06 Benchmark", "#,0",
     "Serie de referencia: ingresantes del pais. Ignora universidad y ubicacion; "
     "respeta periodo, programa y gestion.",
     """CALCULATE (
    [Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion )
)"""),

    ("Indice Ingresantes UCSP", "06 Benchmark", "#,0.0",
     "Ingresantes de la UCSP en base 100 del primer anio seleccionado.",
     """VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Ingresantes UCSP]
VAR Base =
    CALCULATE (
        [Ingresantes UCSP],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100"""),

    ("Indice Ingresantes Macrosur", "06 Benchmark", "#,0.0",
     "Ingresantes de programas impartidos en la macrorregion sur en base 100 del primer anio seleccionado.",
     """VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Ingresantes Macrosur]
VAR Base =
    CALCULATE (
        [Ingresantes Macrosur],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100"""),

    ("Indice Ingresantes Nacional", "06 Benchmark", "#,0.0",
     "Ingresantes del pais en base 100 del primer anio seleccionado.",
     """VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Ingresantes Nacional]
VAR Base =
    CALCULATE (
        [Ingresantes Nacional],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100"""),

    ("Cuota de Mercado en el Sur", "06 Benchmark", "0.00%",
     "Porcentaje de la matricula de la macrorregion sur que capta la seleccion actual.",
     "DIVIDE ( [Matriculados], [Matricula Macrosur] )"),

    # --------------------------------------------------------- selectividad
    ("Tasa de Admision", "07 Selectividad", "0.0%",
     "Admitidos sobre postulaciones. Mas bajo = mas selectivo. Ambos valores "
     "salen del mismo dataset de postulantes, asi que no depende de cruzar fuentes.",
     "DIVIDE ( [Admitidos], [Postulaciones] )"),

    ("Tasa de Admision UCSP", "07 Selectividad", "0.0%",
     "Tasa de admision de la UCSP. Ignora universidad y ubicacion, respeta "
     "periodo, programa y gestion: en una tabla por campo de estudio da la del campo.",
     """CALCULATE (
    [Tasa de Admision],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)"""),

    ("Tasa de Admision Resto del Sur", "07 Selectividad", "0.0%",
     "Tasa de admision de los programas impartidos en la macrorregion sur por "
     "las DEMAS universidades. Es el comparador de la pregunta 4.4: en una tabla "
     "por campo de estudio, cada fila compara a la UCSP con sus equivalentes. "
     "Leer con el filtro de gestion en Privado: las publicas admiten 13-15 % y "
     "arrastran el promedio.",
     """-- Excluye a la UCSP por la misma razon que el benchmark de la 4.3: si no,
-- la universidad se compararia contra un promedio que la contiene.
CALCULATE (
    [Tasa de Admision],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE,
    dim_universidad[es_ucsp] = FALSE
)"""),

    ("Tasa de Admision Privadas del Sur", "07 Selectividad", "0.0%",
     "Tasa de admision de las DEMAS universidades privadas en la macrorregion sur. "
     "Es el comparador justo de la UCSP, que es privada: fija la gestion en vez "
     "de depender de que el usuario la filtre.",
     """CALCULATE (
    [Tasa de Admision Resto del Sur],
    dim_universidad[tipo_gestion] = "Privado"
)"""),

    ("Tasa de Admision Publicas del Sur", "07 Selectividad", "0.0%",
     "Tasa de admision de las universidades publicas de la macrorregion sur. Se "
     "muestra como contexto: admiten entre 13 % y 15 % y arrastran cualquier "
     "promedio que las incluya.",
     """CALCULATE (
    [Tasa de Admision Resto del Sur],
    dim_universidad[tipo_gestion] = "Público"
)"""),

    # -------------------------------------------------------- concentracion
    ("HHI Universidad", "08 Concentracion", "#,0",
     "Indice Herfindahl-Hirschman de la matricula entre programas de la "
     "universidad, escala 0-10000, en el ULTIMO anio del contexto. Alto = "
     "matricula concentrada en pocos programas. Precalculado en fct_concentracion.",
     """-- Ultimo anio en contexto, como los demas indicadores de stock: el HHI de un
-- rango no es el promedio de sus HHI. Medido: con la UCSP y 2021-2025, el
-- promedio daba 1 308; el valor de 2025 es 1 212.
VAR UltimoAnio = MAX ( fct_concentracion[anio] )
RETURN
    CALCULATE ( AVERAGE ( fct_concentracion[hhi] ), dim_periodo[anio] = UltimoAnio )"""),

    ("HHI Mediana Macrosur", "08 Concentracion", "#,0",
     "Mediana del HHI de las universidades con SEDE PRINCIPAL en la macrorregion "
     "sur en el ultimo anio del contexto, como referencia para juzgar si la UCSP "
     "esta mas o menos concentrada que sus pares. Filtra por "
     "dim_universidad[es_macrosur_sede]: fct_concentracion esta a grano anio x "
     "universidad y no se relaciona con dim_ubicacion.",
     """-- La iteracion quita los filtros de universidad (salvo la gestion). Sin eso,
-- un filtro de la UCSP llegaba hasta el CALCULATE interno, las demas
-- universidades del sur quedaban sin valor y la mediana salia en blanco.
VAR UltimoAnio = MAX ( fct_concentracion[anio] )
VAR Universidades =
    CALCULATETABLE (
        VALUES ( fct_concentracion[codigo_inei] ),
        ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
        dim_universidad[es_macrosur_sede] = TRUE,
        dim_periodo[anio] = UltimoAnio
    )
RETURN
    MEDIANX (
        Universidades,
        CALCULATE (
            AVERAGE ( fct_concentracion[hhi] ),
            ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
            dim_periodo[anio] = UltimoAnio
        )
    )"""),

    # ------------------------------------------------------------ tendencia
    # Leen dim_tendencia_programa, una fila por programa con la regresion de
    # 04_tendencias.py sobre ingresantes y sobre matricula. Son SELECTEDVALUE y
    # no AVERAGE: el resultado de una regresion por programa no se promedia
    # entre programas, se deja en blanco.
    # OJO: el segmentador de universidad no llega a dim_programa (no hay
    # relacion entre dimensiones, a proposito). La pagina 3 filtra
    # dim_programa[codigo_inei] a nivel de pagina: ver GUIA_ARMADO.md.
    ("CAGR OLS Ingresantes", "09 Tendencia", "+0.0%;-0.0%;0.0%",
     "Crecimiento anual compuesto de los ingresantes del programa, estimado por "
     "regresion OLS sobre log(ingresantes) 2021-2025. A diferencia de [CAGR "
     "Ingresantes], que solo mira el primer y el ultimo anio, usa los cinco puntos.",
     "SELECTEDVALUE ( dim_tendencia_programa[cagr_ing] )"),

    ("CAGR OLS Matricula", "09 Tendencia", "+0.0%;-0.0%;0.0%",
     "Crecimiento anual compuesto de la matricula del programa por regresion OLS "
     "sobre log(matriculados) 2021-2025. En un programa nuevo sube por "
     "acumulacion de cohortes aunque el ingreso caiga: leer siempre junto a "
     "[CAGR OLS Ingresantes].",
     "SELECTEDVALUE ( dim_tendencia_programa[cagr_mat] )"),

    ("CAGR Campo Sur Ingresantes", "09 Tendencia", "+0.0%;-0.0%;0.0%",
     "CAGR OLS de los ingresantes del mismo campo CINE en la macrorregion sur, "
     "sin la UCSP. Es el benchmark sectorial de la pregunta 4.3.",
     "SELECTEDVALUE ( dim_tendencia_programa[cagr_campo_sur_ing] )"),

    ("CAGR Campo Sur Matricula", "09 Tendencia", "+0.0%;-0.0%;0.0%",
     "CAGR OLS de la matricula del mismo campo CINE en la macrorregion sur, sin la UCSP.",
     "SELECTEDVALUE ( dim_tendencia_programa[cagr_campo_sur_mat] )"),

    ("Delta Ingresantes vs Campo Sur", "09 Tendencia", "+0.0%;-0.0%;0.0%",
     "CAGR OLS de ingresantes del programa menos el de su campo en el sur. "
     "Positivo = gana cuota de ingreso frente a sus equivalentes regionales.",
     "SELECTEDVALUE ( dim_tendencia_programa[delta_campo_sur_ing] )"),

    ("Delta Matricula vs Campo Sur", "09 Tendencia", "+0.0%;-0.0%;0.0%",
     "CAGR OLS de matricula del programa menos el de su campo en el sur.",
     "SELECTEDVALUE ( dim_tendencia_programa[delta_campo_sur_mat] )"),

    ("Programas Evaluados", "09 Tendencia", "#,0",
     "Programas con serie suficiente para la regresion (4 anios o mas con dato). "
     "Es el denominador de las tres tarjetas de lectura.",
     """COALESCE (
    CALCULATE (
        DISTINCTCOUNT ( fct_matricula[programa_sk] ),
        dim_tendencia_programa[lectura] <> "Serie insuficiente"
    ),
    0
)"""),

    ("Programas Crecimiento Confirmado", "09 Tendencia", "#,0",
     "Programas con crecimiento sostenido en ingresantes Y en matricula: en las "
     "dos series, >= 4 anios con dato, p < 0,05 y CAGR >= 3 %.",
     """-- Cuenta en el hecho y no en dim_tendencia_programa: asi respeta los
-- segmentadores de universidad, gestion y ubicacion, que llegan a
-- fct_matricula pero no a la dimension. El filtro sobre la lectura viaja de
-- dim_tendencia_programa a dim_programa por la relacion 1:1 (bidireccional
-- por definicion) y de ahi al hecho.
-- COALESCE: es una medida de tarjeta. Cero programas es una respuesta, no un
-- dato faltante, y una tarjeta en blanco se lee como lo segundo.
COALESCE (
    CALCULATE (
        DISTINCTCOUNT ( fct_matricula[programa_sk] ),
        dim_tendencia_programa[lectura] = "Crecimiento confirmado"
    ),
    0
)"""),

    ("Programas Caida Confirmada", "09 Tendencia", "#,0",
     "Programas con caida sostenida en ingresantes Y en matricula.",
     """COALESCE (
    CALCULATE (
        DISTINCTCOUNT ( fct_matricula[programa_sk] ),
        dim_tendencia_programa[lectura] = "Caida confirmada"
    ),
    0
)"""),

    ("Programas en Alerta", "09 Tendencia", "#,0",
     "Programas cuyo ingreso cae de forma sostenida mientras la matricula aun no "
     "lo refleja: el indicador adelantado ya giro y el rezagado todavia no.",
     """COALESCE (
    CALCULATE (
        DISTINCTCOUNT ( fct_matricula[programa_sk] ),
        dim_tendencia_programa[lectura] = "Alerta: cae el ingreso"
    ),
    0
)"""),

    # ------------------------------------------------- 10 grano semestral
    # Estas dos medidas existen porque fct_matricula paso de 5 periodos anuales
    # a los 12 semestres reales. Lo que antes era un recorte de datos ahora es
    # un eje del modelo, y hay que decir explicitamente que medida respeta ese
    # eje y que medida lo fija.
    ("Matriculados Semestre", "10 Semestral", "#,0",
     "Matriculados del semestre en contexto. Es la medida fiel al grano del "
     "hecho: respeta el slicer de semestre y no impone ninguno. Usar solo en "
     "visuales que tengan el semestre en el eje o en el filtro.",
     """-- La contraparte de [Matriculados]. Aqui el SUM directo es lo correcto
-- PORQUE el semestre forma parte del contexto del visual: si el eje es el
-- semestre, cada punto es un semestre y no hay doble conteo.
SUM ( fct_matricula[matriculados] )"""),

    ("Retencion Intra-anual", "10 Semestral", "0.0%",
     "Matriculados del semestre II sobre los del semestre I del mismo anio. "
     "Por debajo de 100% hay perdida de matricula dentro del anio. No es "
     "desercion exacta: no sigue a las mismas personas, compara volumenes.",
     """-- Este indicador era imposible antes de ampliar la ingesta: con un solo
-- semestre descargado por anio no habia con que comparar. Ahora sale de dos
-- CALCULATE sobre el mismo hecho.
VAR Primero = CALCULATE (
        SUM ( fct_matricula[matriculados] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[semestre] = 1
    )
VAR Segundo = CALCULATE (
        SUM ( fct_matricula[matriculados] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[semestre] = 2
    )
RETURN
    DIVIDE ( Segundo, Primero )"""),

    # --------------------------------------------- 11 egresados y titulacion
    ("Egresados", "11 Egresados", "#,0",
     "Personas distintas que egresan (terminan los cursos) del programa en el "
     "anio. OJO: el slicer de departamento no afecta a esta medida, porque la "
     "fuente de egresados no publica la geografia del local de egreso.",
     """-- Aqui SI se suman los dos semestres, y es correcto: egresar es un
-- FLUJO (ocurre una vez), mientras matricularse es un STOCK (se repite cada
-- semestre). Por eso [Matriculados] fija el semestre y esta medida no.
-- Es la distincion que decide si un SUM sobre un hecho semestral esta bien.
SUM ( fct_egresados[egresados] )"""),

    ("Nota Promedio al Egreso", "11 Egresados", "0.00",
     "Nota promedio ponderada por numero de egresados. Unica medida de "
     "desempeno academico disponible en el portal.",
     """-- Ponderado, no un AVERAGE de los promedios: fct_egresados ya trae una
-- nota PROMEDIO por fila, y promediar promedios de grupos de tamano distinto
-- da un numero que no corresponde a ningun alumno. Se repondera por egresados.
DIVIDE (
    SUMX ( fct_egresados, fct_egresados[nota_promedio] * fct_egresados[egresados] ),
    SUM ( fct_egresados[egresados] )
)"""),

    ("Personas Tituladas", "11 Egresados", "#,0",
     "Personas distintas que obtuvieron un grado o titulo en el anio. Es la "
     "cifra comparable con un conteo de egresados. Solo valido a grano "
     "universidad.",
     """SUM ( fct_titulos[personas] )"""),

    ("Titulados por Egresado", "11 Egresados", "0.00",
     "Personas tituladas en el anio divididas por los egresados del MISMO anio. "
     "NO es una tasa de titulacion: compara dos flujos con rezagos distintos, "
     "porque quien se titula en 2024 egreso varios anios antes. Por encima de "
     "1 significa que se titula mas gente de la que egresa ese anio, lo que "
     "pasa cuando la institucion reduce un rezago acumulado. Se anula si hay "
     "filtro de programa o de ubicacion. "
     "Se calcula sobre el universo comun: solo universidades que reportan las "
     "dos fuentes (control de calidad #17).",
     """-- POR QUE ESTA MEDIDA NO SE LLAMA "Tasa de Titulacion", que era su primer
-- nombre. Una tasa exige que numerador y denominador describan a la MISMA
-- gente, y aqui no lo hacen por dos motivos que se midieron:
--
--   1. Doble conteo. SUM(fct_titulos[titulos]) cuenta EVENTOS: 437 872
--      personas tienen el grado de bachiller Y el titulo profesional, asi que
--      el numerador salia al doble. Se usa [Personas Tituladas], que cuenta
--      personas distintas.
--
--   2. Cohortes distintas. Los titulos se confieren con anos de rezago
--      respecto al egreso. Medido en la UCSP para 2024: 876 grados de
--      bachiller contra 755 egresados -- mas bachilleres que egresados del
--      ano, porque los grados corresponden a quienes egresaron antes.
--
-- Con el nombre anterior la medida reportaba un 206 % y nadie podia saber si
-- era un dato o un error. El nombre nuevo describe exactamente la division que
-- hace, y la limitacion vive en la descripcion, que es lo que Power BI muestra
-- al pasar el cursor.
--
-- GUARDA DE GRANO, por el mismo motivo que [Ratio Alumno Docente]:
-- fct_titulos no se relaciona con dim_programa ni con dim_ubicacion.
-- Y sobre el UNIVERSO COMUN, igual que [Ratio Alumno Docente]: solo
-- universidades que reportan titulos y egresados.
VAR FiltroFino = ISFILTERED ( dim_programa ) || ISFILTERED ( dim_ubicacion )
VAR Comunes =
    FILTER (
        VALUES ( dim_universidad[codigo_inei] ),
        NOT ISBLANK ( [Personas Tituladas] ) && NOT ISBLANK ( [Egresados] )
    )
RETURN
    IF (
        FiltroFino,
        BLANK (),
        DIVIDE ( SUMX ( Comunes, [Personas Tituladas] ), SUMX ( Comunes, [Egresados] ) )
    )"""),

    ("Egresados por Ingresante", "11 Egresados", "0.00",
     "Egresados del anio sobre ingresantes del mismo anio. NO es una tasa de "
     "graduacion: compara dos cohortes distintas, porque quien egresa en 2025 "
     "ingreso cinco anios antes. Sirve para ver si la salida y la entrada "
     "estan en equilibrio, no para medir exito individual. "
     "Se calcula sobre el universo comun: solo universidades que reportan las "
     "dos fuentes (control de calidad #17).",
     """-- La limitacion esta en la descripcion a proposito: la medida es util y
-- barata, pero leerla como "tasa de graduacion" seria un error. Un indicador
-- de cohorte exigiria seguir a las mismas personas, y GUID_PERSONA no permite
-- hacerlo entre datasets distintos del portal.
--
-- GUARDA DE GRANO: fct_egresados no se relaciona con dim_ubicacion. Con un
-- filtro geografico [Ingresantes] se filtraria y [Egresados] no, y el cociente
-- compararia todo el pais contra un departamento.
-- Y sobre el UNIVERSO COMUN: 17 a 43 universidades con ingresantes no
-- reportan egresados segun el anio (control #17), y bajarian el cociente.
VAR Comunes =
    FILTER (
        VALUES ( dim_universidad[codigo_inei] ),
        NOT ISBLANK ( [Egresados] ) && NOT ISBLANK ( [Ingresantes] )
    )
RETURN
    IF (
        ISFILTERED ( dim_ubicacion ),
        BLANK (),
        DIVIDE ( SUMX ( Comunes, [Egresados] ), SUMX ( Comunes, [Ingresantes] ) )
    )"""),

    # ------------------------------------------------ 12 capacidad docente
    # El ratio alumno/docente y el % a tiempo completo son Condiciones Basicas
    # de Calidad del licenciamiento SUNEDU: son los indicadores con los que la
    # reguladora mide a las universidades, asi que el benchmark de la 4.1 deja
    # de ser solo de tamano y pasa a ser de capacidad.
    ("Docentes", "12 Docentes", "#,0",
     "Docentes distintos de pregrado en la serie anual comparable. La fuente "
     "repite al docente por cada grado que acredita; el hecho ya cuenta "
     "personas distintas.",
     """-- Mismo tratamiento que [Matriculados], en los dos ejes: el plantel es un
-- STOCK. Sumar semestres contaria dos veces al mismo profesor, y sumar anios
-- hasta cinco veces.
VAR UltimoAnio =
    CALCULATE (
        MAX ( fct_docentes[anio] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[es_serie_anual] = TRUE
    )
RETURN
    CALCULATE (
        SUM ( fct_docentes[docentes] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[es_serie_anual] = TRUE,
        dim_periodo[anio] = UltimoAnio
    )"""),

    ("% Docentes Tiempo Completo", "12 Docentes", "0.0%",
     "Docentes a tiempo completo o dedicacion exclusiva sobre el total. "
     "Condicion Basica de Calidad del licenciamiento SUNEDU.",
     """-- Numerador al mismo grano que [Docentes]: serie anual y ultimo anio en
-- contexto. Si no, con varios anios el cociente mezclaria granos.
VAR UltimoAnio =
    CALCULATE (
        MAX ( fct_docentes[anio] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[es_serie_anual] = TRUE
    )
VAR Completo =
    CALCULATE (
        SUM ( fct_docentes[docentes_tiempo_completo] ),
        REMOVEFILTERS ( dim_semestre ),
        dim_semestre[es_serie_anual] = TRUE,
        dim_periodo[anio] = UltimoAnio
    )
RETURN
    DIVIDE ( Completo, [Docentes] )"""),

    ("Ratio Alumno Docente", "12 Docentes", "0.0",
     "Matriculados por cada docente, sobre las universidades que reportan las "
     "dos fuentes. Se anula si hay filtro de programa o de ubicacion: la fuente "
     "de docentes no trae programa ni local, asi que a ese grano el ratio "
     "compararia cosas distintas.",
     """-- GUARDA DE GRANO, la misma de [Titulados por Egresado] y por el mismo
-- motivo. Es el error mas facil de cometer con este modelo: filtrar un
-- programa haria caer el numerador a la matricula de ese programa mientras el
-- denominador sigue siendo TODO el plantel de la universidad, y el ratio
-- pareceria de 3 alumnos por docente. Devolver BLANK es la respuesta honesta.
-- La guarda mira las TABLAS, no columnas sueltas: asi cubre cualquier campo
-- de programa o de ubicacion, incluida la macrorregion, que es un filtro
-- obligatorio del enunciado y tampoco llega a fct_docentes.
-- UNIVERSO COMUN: numerador y denominador se suman solo sobre las
-- universidades que reportan LAS DOS fuentes. Un cociente directo mezcla dos
-- universos: medido en 2025, el ratio alumno/docente del pais da 20,9 directo y
-- 19,5 sobre el universo comun, porque hay universidades con matricula y sin
-- docentes reportados. Es el mismo error que producia el 206 % de titulacion
-- (control de calidad #17).
-- Y en UN solo anio, el ultimo del contexto: sin fijarlo, con un rango de
-- anios cada universidad aportaba su propio ultimo anio y el ratio mezclaba
-- fechas (medido: 15,27 contra 15,40 de 2025 en el sur).
VAR FiltroFino = ISFILTERED ( dim_programa ) || ISFILTERED ( dim_ubicacion )
VAR UltimoAnio = MAX ( fct_docentes[anio] )
VAR Ratio =
    CALCULATE (
        VAR Comunes =
            FILTER (
                VALUES ( dim_universidad[codigo_inei] ),
                NOT ISBLANK ( [Docentes] ) && NOT ISBLANK ( [Matriculados] )
            )
        RETURN
            DIVIDE ( SUMX ( Comunes, [Matriculados] ), SUMX ( Comunes, [Docentes] ) ),
        dim_periodo[anio] = UltimoAnio
    )
RETURN
    IF ( FiltroFino, BLANK (), Ratio )"""),

    ("Ratio Alumno Docente Macrosur", "12 Docentes", "0.0",
     "Ratio alumno/docente del conjunto de universidades con sede en la "
     "macrorregion sur, para comparar contra la UCSP.",
     """-- Se filtra por dim_universidad[es_macrosur_sede] y no por dim_ubicacion,
-- porque fct_docentes no se relaciona con dim_ubicacion. La definicion de
-- universidad del sur es la declarada en dim_universidad: aquella cuya sede
-- principal, por volumen de matricula, esta en la macrorregion sur.
-- Llama a [Ratio Alumno Docente] para heredar su guarda de grano.
CALCULATE (
    [Ratio Alumno Docente],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    dim_universidad[es_macrosur_sede] = TRUE
)"""),

    ("Ratio Alumno Docente Nacional", "12 Docentes", "0.0",
     "Ratio alumno/docente del sistema universitario completo.",
     """-- Llama a [Ratio Alumno Docente] para heredar su guarda de grano.
CALCULATE (
    [Ratio Alumno Docente],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] )
)"""),

    # ----------------------------------------------------------- 13 narrativa
    # Titulares de pagina para el tablero ejecutivo. Son texto, no numeros: se
    # reescriben con los filtros, de modo que la frase de arriba de cada pagina
    # dice siempre lo que muestran los visuales de abajo.
    ("Rango de Anios", "13 Narrativa", "",
     "Rango de anios seleccionado, para los titulos de los visuales.",
     """VAR Desde = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Hasta = MAXX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
RETURN
    IF ( Desde = Hasta, FORMAT ( Desde, "0" ), FORMAT ( Desde, "0" ) & "-" & FORMAT ( Hasta, "0" ) )"""),

    ("Titular Resumen", "13 Narrativa", "",
     "Frase de cabecera del resumen ejecutivo y de la pagina 4.1.",
     """VAR MatU = [CAGR Matricula UCSP]
VAR IngU = [CAGR Ingresantes UCSP]
VAR IngS = [CAGR Ingresantes Macrosur]
RETURN
    IF (
        NOT ISBLANK ( MatU ) && NOT ISBLANK ( IngU ),
        "En " & [Rango de Anios] & ", la matrícula de la UCSP "
            & IF ( MatU >= 0, "crece ", "cae " ) & FORMAT ( ABS ( MatU ), "0.0%" )
            & " al año y su ingreso "
            & IF ( IngU >= 0, "crece ", "cae " ) & FORMAT ( ABS ( IngU ), "0.0%" )
            & "; el ingreso del sur "
            & IF ( IngS >= 0, "crece ", "cae " ) & FORMAT ( ABS ( IngS ), "0.0%" ) & "."
    )"""),

    ("Titular Demanda", "13 Narrativa", "",
     "Frase de cabecera de la pagina 4.2: el programa de mayor y de menor ingreso "
     "dentro de los filtros activos.",
     """VAR Programas =
    FILTER (
        ADDCOLUMNS ( ALLSELECTED ( dim_programa[nombre_programa] ), "@v", [Ingresantes] ),
        [@v] >= 10
    )
VAR Mayor = TOPN ( 1, Programas, [@v], DESC )
VAR Menor = TOPN ( 1, Programas, [@v], ASC )
RETURN
    IF (
        NOT ISEMPTY ( Programas ),
        "Mayor ingreso: " & MAXX ( Mayor, dim_programa[nombre_programa] )
            & " (" & FORMAT ( MAXX ( Mayor, [@v] ), "#,0" ) & "). Menor: "
            & MAXX ( Menor, dim_programa[nombre_programa] )
            & " (" & FORMAT ( MAXX ( Menor, [@v] ), "#,0" ) & ")."
    )"""),

    ("Titular Tendencia", "13 Narrativa", "",
     "Frase de cabecera de la pagina 4.3, con singular y plural resueltos.",
     """VAR Conf = [Programas Crecimiento Confirmado]
VAR Caida = [Programas Caida Confirmada]
VAR Alerta = [Programas en Alerta]
VAR TxtConf =
    IF (
        Conf = 0,
        "Ningún programa crece",
        FORMAT ( Conf, "0" ) & IF ( Conf = 1, " programa crece", " programas crecen" )
    ) & " en ingreso y matrícula a la vez"
VAR TxtCaida = FORMAT ( Caida, "0" ) & IF ( Caida = 1, " cae", " caen" ) & " en las dos series"
VAR TxtAlerta =
    FORMAT ( Alerta, "0" ) & IF ( Alerta = 1, " ya pierde", " ya pierden" )
        & " ingreso sin que la matrícula lo refleje"
RETURN
    CONCATENATE ( TxtConf & "; " & TxtCaida & " y " & TxtAlerta, "." )"""),

    ("Titular Selectividad", "13 Narrativa", "",
     "Frase de cabecera de la pagina 4.4: la UCSP frente a sus pares privados. "
     "Una diferencia menor a 3 puntos se lee como similar: no se afirma mas de "
     "lo que el dato sostiene.",
     """VAR U = [Tasa de Admision UCSP]
VAR P = [Tasa de Admision Privadas del Sur]
RETURN
    IF (
        NOT ISBLANK ( U ) && NOT ISBLANK ( P ),
        "La UCSP admite el " & FORMAT ( U, "0%" ) & " de sus postulaciones; las demás privadas del sur, el "
            & FORMAT ( P, "0%" ) & ". "
            & IF (
                ABS ( U - P ) < 0.03,
                "Su selectividad es similar a la de sus pares.",
                IF ( U < P, "Es más selectiva que sus pares.", "Es menos selectiva que sus pares." )
            )
    )"""),
]

CSX_CABECERA = """// Script de Tabular Editor: crea todas las medidas del modelo.
//
// Uso:
//   1. Abrir el .pbix en Power BI Desktop con el modelo ya cargado y relacionado.
//   2. Herramientas externas -> Tabular Editor.
//   3. Pestana C# Script, pegar este archivo, F5.
//   4. Volver a Power BI Desktop y guardar.
//
// Generado por 05_powerbi.py. No editar a mano: editar la lista MEDIDAS de ese
// script y volver a generarlo, para que el catalogo documentado no se desincronice.

// Las medidas viven en una tabla propia, no colgadas de un hecho: el panel de
// campos queda limpio y los hechos pueden ocultarse enteros.
var tabla = Model.Tables.Contains("_Medidas")
    ? Model.Tables["_Medidas"]
    : Model.AddCalculatedTable("_Medidas", "ROW ( \\"Medidas\\", BLANK () )");

// Columna de ayuda para el filtro de pagina de la pregunta 4.3: el segmentador
// de universidad no llega a dim_programa, porque las dimensiones no se
// relacionan entre si.
var programa = Model.Tables["dim_programa"];
if (!programa.Columns.Contains("es_ucsp"))
    programa.AddCalculatedColumn("es_ucsp",
        "LOOKUPVALUE ( dim_universidad[es_ucsp], dim_universidad[codigo_inei], dim_programa[codigo_inei] )");

Measure m;

"""


def escapar_csharp(texto):
    return texto.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def generar_csx():
    partes = [CSX_CABECERA]
    for nombre, carpeta, formato, descripcion, dax in MEDIDAS:
        partes.append(
            f'm = tabla.AddMeasure("{nombre}", "{escapar_csharp(dax)}");\n'
            f'm.DisplayFolder = "{carpeta}";\n'
            f'm.FormatString = "{formato}";\n'
            f'm.Description = "{escapar_csharp(descripcion)}";\n'
        )
    partes.append(f'\nInfo("{len(MEDIDAS)} medidas creadas.");\n')
    return "\n".join(partes)


def generar_dax():
    partes = ["// Catalogo de medidas en texto plano (respaldo de medidas.csx).\n"]
    carpeta_actual = None
    for nombre, carpeta, formato, descripcion, dax in MEDIDAS:
        if carpeta != carpeta_actual:
            partes.append(f"\n// {'=' * 68}\n// {carpeta}\n// {'=' * 68}\n")
            carpeta_actual = carpeta
        partes.append(f"\n// {descripcion}\n// formato: {formato}\n{nombre} =\n{dax}\n")
    return "".join(partes)


def generar_catalogo():
    lineas = [
        "# Catálogo de medidas DAX",
        "",
        f"{len(MEDIDAS)} medidas explícitas, organizadas en carpetas de visualización.",
        "Generado automáticamente por `05_powerbi.py` a partir de la misma definición",
        "que produce `powerbi/medidas.csx`, de modo que catálogo y modelo no pueden",
        "quedar desincronizados.",
        "",
        "## Convenciones aplicadas",
        "",
        "- **Medidas explícitas**: ninguna agregación implícita arrastrada a un visual.",
        "- **`VAR`**: separa cálculo de presentación y evalúa cada subexpresión una sola vez.",
        "- **`DIVIDE()`**: en todo cociente, devuelve BLANK en lugar de error al dividir entre cero.",
        "- **`REMOVEFILTERS()`** en lugar de `ALL()`: expresa la intención de quitar un filtro concreto.",
        "- **Sin time intelligence**: `dim_periodo[anio]` es un entero, no una fecha, así que el",
        "  desplazamiento interanual es explícito (`anio - 1`) en vez de `SAMEPERIODLASTYEAR`.",
        "- **`ALLSELECTED` en los rankings**: el ranking se recalcula dentro de los filtros",
        "  activos, que es lo que exige el requerimiento 4.2.",
        "",
    ]
    carpeta_actual = None
    for nombre, carpeta, formato, descripcion, dax in MEDIDAS:
        if carpeta != carpeta_actual:
            lineas += ["", f"## {carpeta}", ""]
            carpeta_actual = carpeta
        lineas += [
            f"### `{nombre}`",
            "",
            f"{descripcion}",
            "",
            f"*Formato:* `{formato}`",
            "",
            "```dax",
            f"{nombre} =",
            dax,
            "```",
            "",
        ]
    return "\n".join(lineas)


def main():
    POWERBI.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    (POWERBI / "medidas.csx").write_text(generar_csx(), encoding="utf-8")
    (POWERBI / "medidas.dax").write_text(generar_dax(), encoding="utf-8")
    (DOCS / "catalogo_medidas.md").write_text(generar_catalogo(), encoding="utf-8")

    carpetas = sorted({c for _, c, *_ in MEDIDAS})
    print(f"{len(MEDIDAS)} medidas en {len(carpetas)} carpetas:")
    for carpeta in carpetas:
        n = sum(1 for _, c, *_ in MEDIDAS if c == carpeta)
        print(f"  {carpeta:28s} {n}")
    print(f"\n  {POWERBI / 'medidas.csx'}")
    print(f"  {POWERBI / 'medidas.dax'}")
    print(f"  {DOCS / 'catalogo_medidas.md'}")


if __name__ == "__main__":
    main()
