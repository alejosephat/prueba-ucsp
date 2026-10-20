# Catálogo de medidas DAX

79 medidas explícitas del modelo entregado (`UCSP_Benchmark.pbix`), en la tabla
`_Medidas` y organizadas en carpetas de visualización.

## Convenciones aplicadas

- **Medidas explícitas**: ninguna agregación implícita arrastrada a un visual.
- **`VAR`**: separa cálculo de presentación y evalúa cada subexpresión una sola vez.
- **`DIVIDE()`**: en todo cociente, devuelve BLANK en lugar de error al dividir entre cero.
- **`REMOVEFILTERS()`** en lugar de `ALL()`: expresa la intención de quitar un filtro concreto.
- **Sin time intelligence**: `dim_periodo[anio]` es un entero, no una fecha, así que el
  desplazamiento interanual es explícito (`anio - 1`) en vez de `SAMEPERIODLASTYEAR`.
- **`ALLSELECTED` en los rankings**: el ranking se recalcula dentro de los filtros
  activos, que es lo que exige el requerimiento 4.2.


## 01 Base

### `Ingresantes`

Personas distintas que ingresan a un programa de pregrado en el anio.

*Formato:* `#,0`

```dax
Ingresantes =
SUM ( fct_ingresantes[ingresantes] )
```

### `Matriculados`

Personas distintas matriculadas en pregrado en la serie anual comparable (un semestre fijo por anio). Es un stock: con varios anios en contexto devuelve el del ULTIMO anio, no la suma. El slicer de semestre no la afecta: para eso esta [Matriculados Semestre].

*Formato:* `#,0`

```dax
Matriculados =
-- La matricula es un STOCK: la misma persona aparece en cada semestre y en
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
    )
```

### `Ingresantes Ultimo Anio`

Ingresantes del ULTIMO anio del contexto. [Ingresantes] es un flujo y suma el rango, que es lo correcto en una serie; esta es la cifra de la ficha.

*Formato:* `#,0`

```dax
Ingresantes Ultimo Anio =
VAR UltimoAnio = MAX ( fct_ingresantes[anio] )
RETURN
    CALCULATE ( [Ingresantes], dim_periodo[anio] = UltimoAnio )
```

### `Postulaciones`

Postulaciones recibidas (una persona puede postular a varios programas).

*Formato:* `#,0`

```dax
Postulaciones =
SUM ( fct_postulantes[postulaciones] )
```

### `Postulantes`

Personas distintas que postulan. Menor que Postulaciones por multipostulacion.

*Formato:* `#,0`

```dax
Postulantes =
SUM ( fct_postulantes[postulantes] )
```

### `Admitidos`

Postulaciones que resultaron en ingreso, segun la propia fuente de postulantes.

*Formato:* `#,0`

```dax
Admitidos =
SUM ( fct_postulantes[admitidos] )
```

### `Programas Activos`

Programas con matricula mayor a cero en el ULTIMO anio del contexto.

*Formato:* `#,0`

```dax
Programas Activos =
-- El filtro de semestre va por la misma razon que en [Matriculados]. Y es un
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
    )
```


## 02 Variacion interanual

### `Matriculados AA`

Matriculados del anio anterior. BLANK si el anio previo no esta en la serie.

*Formato:* `#,0`

```dax
Matriculados AA =
VAR AnioActual = MAX ( dim_periodo[anio] )
RETURN
    CALCULATE (
        [Matriculados],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioActual - 1
    )
```

### `Var. Matricula (abs)`

Diferencia absoluta de matriculados contra el anio anterior. Con varios anios en contexto, la del ultimo.

*Formato:* `+#,0;-#,0;0`

```dax
Var. Matricula (abs) =
-- Las dos puntas se fijan a un anio concreto. Con varios anios en contexto
-- (la fila de total) la medida devuelve la variacion del ULTIMO anio contra
-- el anterior. Sin fijar la punta actual, en [Ingresantes] -que es un flujo y
-- si se suma- la fila de total compararia todo el rango contra un solo anio.
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior = [Matriculados AA]
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), Actual - Anterior )
```

### `Var. Matricula (%)`

Variacion porcentual de matriculados contra el anio anterior. Con varios anios en contexto, la del ultimo.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
Var. Matricula (%) =
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior = [Matriculados AA]
RETURN
    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )
```

### `Ingresantes AA`

Ingresantes del anio anterior.

*Formato:* `#,0`

```dax
Ingresantes AA =
VAR AnioActual = MAX ( dim_periodo[anio] )
RETURN
    CALCULATE (
        [Ingresantes],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioActual - 1
    )
```

### `Var. Ingresantes (abs)`

Diferencia absoluta de ingresantes contra el anio anterior. Con varios anios en contexto, la del ultimo.

*Formato:* `+#,0;-#,0;0`

```dax
Var. Ingresantes (abs) =
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior = [Ingresantes AA]
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), Actual - Anterior )
```

### `Var. Ingresantes (%)`

Variacion porcentual de ingresantes contra el anio anterior. Con varios anios en contexto, la del ultimo.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
Var. Ingresantes (%) =
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior = [Ingresantes AA]
RETURN
    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )
```

### `Var. Cuota del Sur (pp)`

Cambio de la cuota de la matricula del sur contra el anio anterior, en puntos porcentuales.

*Formato:* `+0.00" pp";-0.00" pp";0.00" pp"`

```dax
Var. Cuota del Sur (pp) =
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Cuota de Mercado en el Sur], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [Cuota de Mercado en el Sur], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) * 100 )
```

### `Var. Programas Activos`

Programas activos del ultimo anio menos los del anio anterior.

*Formato:* `+0;-0;0`

```dax
Var. Programas Activos =
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Programas Activos], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [Programas Activos], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) )
```

### `Var. HHI`

Cambio del HHI contra el anio anterior. Negativo = la matricula se diversifica.

*Formato:* `+#,0;-#,0;0`

```dax
Var. HHI =
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [HHI Universidad], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [HHI Universidad], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) )
```

### `Var. Tasa de Admision UCSP (pp)`

Cambio de la tasa de admision de la UCSP contra el anio anterior, en puntos porcentuales.

*Formato:* `+0.0" pp";-0.0" pp";0.0" pp"`

```dax
Var. Tasa de Admision UCSP (pp) =
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Tasa de Admision UCSP], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [Tasa de Admision UCSP], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) * 100 )
```

### `Var. Postulaciones (%)`

Variacion porcentual de las postulaciones contra el anio anterior.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
Var. Postulaciones (%) =
VAR AnioActual = MAX ( dim_periodo[anio] )
VAR Actual =
    CALCULATE ( [Postulaciones], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )
VAR Anterior =
    CALCULATE ( [Postulaciones], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )
RETURN
    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )
```


## 03 Participacion

### `% Participacion en su Universidad`

Peso del programa dentro de la matricula de SU universidad. El denominador quita el filtro de programa pero reimpone la universidad a la que pertenece el programa del contexto, para que no se escape al total nacional.

*Formato:* `0.0%`

```dax
% Participacion en su Universidad =
VAR MatriculaPrograma = [Matriculados]
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
    DIVIDE ( MatriculaPrograma, MatriculaUniversidad )
```


## 04 Ranking

### `Ranking Programa`

Posicion del programa por matricula. ALLSELECTED (no ALL) hace que el ranking se recalcule dentro de los filtros activos de universidad, departamento, gestion y periodo.

*Formato:* `#,0`

```dax
Ranking Programa =
IF (
    NOT ISBLANK ( [Matriculados] ),
    RANKX (
        ALLSELECTED ( dim_programa[nombre_programa] ),
        [Matriculados],
        ,
        DESC,
        DENSE
    )
)
```

### `Ranking Programa (Ingresantes)`

Posicion del programa por ingresantes, tambien sensible a los filtros.

*Formato:* `#,0`

```dax
Ranking Programa (Ingresantes) =
IF (
    NOT ISBLANK ( [Ingresantes] ),
    RANKX (
        ALLSELECTED ( dim_programa[nombre_programa] ),
        [Ingresantes],
        ,
        DESC,
        DENSE
    )
)
```

### `Ranking Programa Inverso`

Posicion desde la cola, para el bottom-5. Excluye programas por debajo del umbral minimo: sin eso el fondo lo ocupan programas que abrieron ese anio con 2 o 3 alumnos y el visual deja de ser informativo.

*Formato:* `#,0`

```dax
Ranking Programa Inverso =
VAR Umbral = 10
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
    )
```

### `Ranking Programa Inverso (Ingresantes)`

Posicion desde la cola por ingresantes, para el bottom-5 de ingreso. Mismo umbral minimo que [Ranking Programa Inverso].

*Formato:* `#,0`

```dax
Ranking Programa Inverso (Ingresantes) =
VAR Umbral = 10
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
    )
```


## 05 Crecimiento

### `CAGR Matricula`

Tasa de crecimiento anual compuesta de la matricula entre el primer y el ultimo anio seleccionados. BLANK si hay un solo anio o si el inicio es cero.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Matricula =
VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )
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
    )
```

### `CAGR Ingresantes`

Tasa de crecimiento anual compuesta de los ingresantes del rango seleccionado.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Ingresantes =
VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )
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
    )
```

### `Crecimiento Acumulado %`

Variacion total de la matricula entre el primer y el ultimo anio seleccionados.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
Crecimiento Acumulado % =
VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )
VAR AnioIni = MINX ( AniosVisibles, dim_periodo[anio] )
VAR AnioFin = MAXX ( AniosVisibles, dim_periodo[anio] )
VAR ValorIni =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioIni )
VAR ValorFin =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioFin )
RETURN
    DIVIDE ( ValorFin - ValorIni, ValorIni )
```


## 06 Benchmark

### `Matricula UCSP`

Serie de referencia: matricula de la UCSP. Como todos los comparadores, ignora la universidad y la ubicacion (lo que define la cohorte) y respeta periodo, programa y gestion, que es lo que hace comparables las series.

*Formato:* `#,0`

```dax
Matricula UCSP =
-- ALLEXCEPT y no REMOVEFILTERS ( dim_universidad ): el comparador debe
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
)
```

### `Matricula Macrosur`

Matricula IMPARTIDA en locales de la macrorregion sur, sea cual sea la sede de la universidad. Es un concepto distinto de es_macrosur_sede, que clasifica a la universidad entera: una universidad de Lima con filial en Cusco aporta a esta medida, pero no cuenta como universidad del sur.

*Formato:* `#,0`

```dax
Matricula Macrosur =
CALCULATE (
    [Matriculados],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE
)
```

### `Matricula Nacional`

Serie de referencia: matricula nacional. Ignora universidad y ubicacion y respeta periodo, programa y gestion, igual que las otras dos series del grupo, para que las tres sean comparables.

*Formato:* `#,0`

```dax
Matricula Nacional =
CALCULATE (
    [Matriculados],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion )
)
```

### `Indice Matricula UCSP`

Matricula de la UCSP en base 100 del primer anio seleccionado. La indexacion es lo que hace comparables tres series de escalas muy distintas (UCSP ~8 mil, sur ~200 mil, nacional ~1.6 millones) en un mismo grafico.

*Formato:* `#,0.0`

```dax
Indice Matricula UCSP =
VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Matricula UCSP]
VAR Base =
    CALCULATE (
        [Matricula UCSP],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100
```

### `Indice Matricula Macrosur`

Matricula de la macrorregion sur en base 100 del primer anio seleccionado.

*Formato:* `#,0.0`

```dax
Indice Matricula Macrosur =
VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Matricula Macrosur]
VAR Base =
    CALCULATE (
        [Matricula Macrosur],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100
```

### `Indice Matricula Nacional`

Matricula nacional en base 100 del primer anio seleccionado.

*Formato:* `#,0.0`

```dax
Indice Matricula Nacional =
VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Matricula Nacional]
VAR Base =
    CALCULATE (
        [Matricula Nacional],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100
```

### `CAGR Matricula UCSP`

CAGR de la matricula de la UCSP en el rango de anios seleccionado.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Matricula UCSP =
CALCULATE (
    [CAGR Matricula],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)
```

### `CAGR Matricula Macrosur`

CAGR de la matricula de programas impartidos en la macrorregion sur en el rango de anios seleccionado.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Matricula Macrosur =
CALCULATE (
    [CAGR Matricula],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE
)
```

### `CAGR Matricula Nacional`

CAGR de la matricula del pais en el rango de anios seleccionado.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Matricula Nacional =
CALCULATE (
    [CAGR Matricula],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion )
)
```

### `CAGR Ingresantes UCSP`

CAGR de los ingresantes de la UCSP en el rango de anios seleccionado.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Ingresantes UCSP =
CALCULATE (
    [CAGR Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)
```

### `CAGR Ingresantes Macrosur`

CAGR de los ingresantes de programas impartidos en la macrorregion sur en el rango de anios seleccionado.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Ingresantes Macrosur =
CALCULATE (
    [CAGR Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE
)
```

### `CAGR Ingresantes Nacional`

CAGR de los ingresantes del pais en el rango de anios seleccionado.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Ingresantes Nacional =
CALCULATE (
    [CAGR Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion )
)
```

### `Ingresantes UCSP`

Serie de referencia: ingresantes de la UCSP. Ignora universidad y ubicacion; respeta periodo, programa y gestion.

*Formato:* `#,0`

```dax
Ingresantes UCSP =
CALCULATE (
    [Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)
```

### `Ingresantes Macrosur`

Serie de referencia: ingresantes de programas impartidos en la macrorregion sur. Ignora universidad y ubicacion; respeta periodo, programa y gestion.

*Formato:* `#,0`

```dax
Ingresantes Macrosur =
CALCULATE (
    [Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE
)
```

### `Ingresantes Nacional`

Serie de referencia: ingresantes del pais. Ignora universidad y ubicacion; respeta periodo, programa y gestion.

*Formato:* `#,0`

```dax
Ingresantes Nacional =
CALCULATE (
    [Ingresantes],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion )
)
```

### `Indice Ingresantes UCSP`

Ingresantes de la UCSP en base 100 del primer anio seleccionado.

*Formato:* `#,0.0`

```dax
Indice Ingresantes UCSP =
VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Ingresantes UCSP]
VAR Base =
    CALCULATE (
        [Ingresantes UCSP],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100
```

### `Indice Ingresantes Macrosur`

Ingresantes de programas impartidos en la macrorregion sur en base 100 del primer anio seleccionado.

*Formato:* `#,0.0`

```dax
Indice Ingresantes Macrosur =
VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Ingresantes Macrosur]
VAR Base =
    CALCULATE (
        [Ingresantes Macrosur],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100
```

### `Indice Ingresantes Nacional`

Ingresantes del pais en base 100 del primer anio seleccionado.

*Formato:* `#,0.0`

```dax
Indice Ingresantes Nacional =
VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Serie = [Ingresantes Nacional]
VAR Base =
    CALCULATE (
        [Ingresantes Nacional],
        REMOVEFILTERS ( dim_periodo ),
        dim_periodo[anio] = AnioBase
    )
RETURN
    DIVIDE ( Serie, Base ) * 100
```

### `Cuota de Mercado en el Sur`

Porcentaje de la matricula de la macrorregion sur que capta la seleccion actual.

*Formato:* `0.00%`

```dax
Cuota de Mercado en el Sur =
DIVIDE ( [Matriculados], [Matricula Macrosur] )
```


## 07 Selectividad

### `Tasa de Admision`

Admitidos sobre postulaciones. Mas bajo = mas selectivo. Ambos valores salen del mismo dataset de postulantes, asi que no depende de cruzar fuentes.

*Formato:* `0.0%`

```dax
Tasa de Admision =
DIVIDE ( [Admitidos], [Postulaciones] )
```

### `Tasa de Admision UCSP`

Tasa de admision de la UCSP. Ignora universidad y ubicacion, respeta periodo, programa y gestion: en una tabla por campo de estudio da la del campo.

*Formato:* `0.0%`

```dax
Tasa de Admision UCSP =
CALCULATE (
    [Tasa de Admision],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_universidad[es_ucsp] = TRUE
)
```

### `Tasa de Admision Resto del Sur`

Tasa de admision de los programas impartidos en la macrorregion sur por las DEMAS universidades. Es el comparador de la pregunta 4.4: en una tabla por campo de estudio, cada fila compara a la UCSP con sus equivalentes. Leer con el filtro de gestion en Privado: las publicas admiten 13-15 % y arrastran el promedio.

*Formato:* `0.0%`

```dax
Tasa de Admision Resto del Sur =
-- Excluye a la UCSP por la misma razon que el benchmark de la 4.3: si no,
-- la universidad se compararia contra un promedio que la contiene.
CALCULATE (
    [Tasa de Admision],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    REMOVEFILTERS ( dim_ubicacion ),
    dim_ubicacion[es_macrosur] = TRUE,
    dim_universidad[es_ucsp] = FALSE
)
```

### `Tasa de Admision Privadas del Sur`

Tasa de admision de las DEMAS universidades privadas en la macrorregion sur. Es el comparador justo de la UCSP, que es privada: fija la gestion en vez de depender de que el usuario la filtre.

*Formato:* `0.0%`

```dax
Tasa de Admision Privadas del Sur =
CALCULATE (
    [Tasa de Admision Resto del Sur],
    dim_universidad[tipo_gestion] = "Privado"
)
```

### `Tasa de Admision Publicas del Sur`

Tasa de admision de las universidades publicas de la macrorregion sur. Se muestra como contexto: admiten entre 13 % y 15 % y arrastran cualquier promedio que las incluya.

*Formato:* `0.0%`

```dax
Tasa de Admision Publicas del Sur =
CALCULATE (
    [Tasa de Admision Resto del Sur],
    dim_universidad[tipo_gestion] = "Público"
)
```


## 08 Concentracion

### `HHI Universidad`

Indice Herfindahl-Hirschman de la matricula entre programas de la universidad, escala 0-10000, en el ULTIMO anio del contexto. Alto = matricula concentrada en pocos programas. Precalculado en fct_concentracion.

*Formato:* `#,0`

```dax
HHI Universidad =
-- Ultimo anio en contexto, como los demas indicadores de stock: el HHI de un
-- rango no es el promedio de sus HHI. Medido: con la UCSP y 2021-2025, el
-- promedio daba 1 308; el valor de 2025 es 1 212.
VAR UltimoAnio = MAX ( fct_concentracion[anio] )
RETURN
    CALCULATE ( AVERAGE ( fct_concentracion[hhi] ), dim_periodo[anio] = UltimoAnio )
```

### `HHI Mediana Macrosur`

Mediana del HHI de las universidades con SEDE PRINCIPAL en la macrorregion sur en el ultimo anio del contexto, como referencia para juzgar si la UCSP esta mas o menos concentrada que sus pares. Filtra por dim_universidad[es_macrosur_sede]: fct_concentracion esta a grano anio x universidad y no se relaciona con dim_ubicacion.

*Formato:* `#,0`

```dax
HHI Mediana Macrosur =
-- La iteracion quita los filtros de universidad (salvo la gestion). Sin eso,
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
    )
```


## 09 Tendencia

### `CAGR OLS Ingresantes`

Crecimiento anual compuesto de los ingresantes del programa, estimado por regresion OLS sobre log(ingresantes) 2021-2025. A diferencia de [CAGR Ingresantes], que solo mira el primer y el ultimo anio, usa los cinco puntos.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR OLS Ingresantes =
SELECTEDVALUE ( dim_tendencia_programa[cagr_ing] )
```

### `CAGR OLS Matricula`

Crecimiento anual compuesto de la matricula del programa por regresion OLS sobre log(matriculados) 2021-2025. En un programa nuevo sube por acumulacion de cohortes aunque el ingreso caiga: leer siempre junto a [CAGR OLS Ingresantes].

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR OLS Matricula =
SELECTEDVALUE ( dim_tendencia_programa[cagr_mat] )
```

### `CAGR Campo Sur Ingresantes`

CAGR OLS de los ingresantes del mismo campo CINE en la macrorregion sur, sin la UCSP. Es el benchmark sectorial de la pregunta 4.3.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Campo Sur Ingresantes =
SELECTEDVALUE ( dim_tendencia_programa[cagr_campo_sur_ing] )
```

### `CAGR Campo Sur Matricula`

CAGR OLS de la matricula del mismo campo CINE en la macrorregion sur, sin la UCSP.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
CAGR Campo Sur Matricula =
SELECTEDVALUE ( dim_tendencia_programa[cagr_campo_sur_mat] )
```

### `Delta Ingresantes vs Campo Sur`

CAGR OLS de ingresantes del programa menos el de su campo en el sur. Positivo = gana cuota de ingreso frente a sus equivalentes regionales.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
Delta Ingresantes vs Campo Sur =
SELECTEDVALUE ( dim_tendencia_programa[delta_campo_sur_ing] )
```

### `Delta Matricula vs Campo Sur`

CAGR OLS de matricula del programa menos el de su campo en el sur.

*Formato:* `+0.0%;-0.0%;0.0%`

```dax
Delta Matricula vs Campo Sur =
SELECTEDVALUE ( dim_tendencia_programa[delta_campo_sur_mat] )
```

### `Programas Evaluados`

Programas con serie suficiente para la regresion (4 anios o mas con dato). Es el denominador de las tres tarjetas de lectura.

*Formato:* `#,0`

```dax
Programas Evaluados =
COALESCE (
    CALCULATE (
        DISTINCTCOUNT ( fct_matricula[programa_sk] ),
        dim_tendencia_programa[lectura] <> "Serie insuficiente"
    ),
    0
)
```

### `Programas Crecimiento Confirmado`

Programas con crecimiento sostenido en ingresantes Y en matricula: en las dos series, >= 4 anios con dato, p < 0,05 y CAGR >= 3 %.

*Formato:* `#,0`

```dax
Programas Crecimiento Confirmado =
-- Cuenta en el hecho y no en dim_tendencia_programa: asi respeta los
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
)
```

### `Programas Caida Confirmada`

Programas con caida sostenida en ingresantes Y en matricula.

*Formato:* `#,0`

```dax
Programas Caida Confirmada =
COALESCE (
    CALCULATE (
        DISTINCTCOUNT ( fct_matricula[programa_sk] ),
        dim_tendencia_programa[lectura] = "Caida confirmada"
    ),
    0
)
```

### `Programas en Alerta`

Programas cuyo ingreso cae de forma sostenida mientras la matricula aun no lo refleja: el indicador adelantado ya giro y el rezagado todavia no.

*Formato:* `#,0`

```dax
Programas en Alerta =
COALESCE (
    CALCULATE (
        DISTINCTCOUNT ( fct_matricula[programa_sk] ),
        dim_tendencia_programa[lectura] = "Alerta: cae el ingreso"
    ),
    0
)
```


## 10 Semestral

### `Matriculados Semestre`

Matriculados del semestre en contexto. Es la medida fiel al grano del hecho: respeta el slicer de semestre y no impone ninguno. Usar solo en visuales que tengan el semestre en el eje o en el filtro.

*Formato:* `#,0`

```dax
Matriculados Semestre =
-- La contraparte de [Matriculados]. Aqui el SUM directo es lo correcto
-- PORQUE el semestre forma parte del contexto del visual: si el eje es el
-- semestre, cada punto es un semestre y no hay doble conteo.
SUM ( fct_matricula[matriculados] )
```

### `Retencion Intra-anual`

Matriculados del semestre II sobre los del semestre I del mismo anio. Por debajo de 100% hay perdida de matricula dentro del anio. No es desercion exacta: no sigue a las mismas personas, compara volumenes.

*Formato:* `0.0%`

```dax
Retencion Intra-anual =
-- Este indicador era imposible antes de ampliar la ingesta: con un solo
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
    DIVIDE ( Segundo, Primero )
```


## 11 Egresados

### `Egresados`

Personas distintas que egresan (terminan los cursos) del programa en el anio. OJO: el slicer de departamento no afecta a esta medida, porque la fuente de egresados no publica la geografia del local de egreso.

*Formato:* `#,0`

```dax
Egresados =
-- Aqui SI se suman los dos semestres, y es correcto: egresar es un
-- FLUJO (ocurre una vez), mientras matricularse es un STOCK (se repite cada
-- semestre). Por eso [Matriculados] fija el semestre y esta medida no.
-- Es la distincion que decide si un SUM sobre un hecho semestral esta bien.
SUM ( fct_egresados[egresados] )
```

### `Nota Promedio al Egreso`

Nota promedio ponderada por numero de egresados. Unica medida de desempeno academico disponible en el portal.

*Formato:* `0.00`

```dax
Nota Promedio al Egreso =
-- Ponderado, no un AVERAGE de los promedios: fct_egresados ya trae una
-- nota PROMEDIO por fila, y promediar promedios de grupos de tamano distinto
-- da un numero que no corresponde a ningun alumno. Se repondera por egresados.
DIVIDE (
    SUMX ( fct_egresados, fct_egresados[nota_promedio] * fct_egresados[egresados] ),
    SUM ( fct_egresados[egresados] )
)
```

### `Personas Tituladas`

Personas distintas que obtuvieron un grado o titulo en el anio. Es la cifra comparable con un conteo de egresados. Solo valido a grano universidad.

*Formato:* `#,0`

```dax
Personas Tituladas =
SUM ( fct_titulos[personas] )
```

### `Titulados por Egresado`

Personas tituladas en el anio divididas por los egresados del MISMO anio. NO es una tasa de titulacion: compara dos flujos con rezagos distintos, porque quien se titula en 2024 egreso varios anios antes. Por encima de 1 significa que se titula mas gente de la que egresa ese anio, lo que pasa cuando la institucion reduce un rezago acumulado. Se anula si hay filtro de programa o de ubicacion. Se calcula sobre el universo comun: solo universidades que reportan las dos fuentes (control de calidad #17).

*Formato:* `0.00`

```dax
Titulados por Egresado =
-- POR QUE ESTA MEDIDA NO SE LLAMA "Tasa de Titulacion", que era su primer
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
    )
```

### `Egresados por Ingresante`

Egresados del anio sobre ingresantes del mismo anio. NO es una tasa de graduacion: compara dos cohortes distintas, porque quien egresa en 2025 ingreso cinco anios antes. Sirve para ver si la salida y la entrada estan en equilibrio, no para medir exito individual. Se calcula sobre el universo comun: solo universidades que reportan las dos fuentes (control de calidad #17).

*Formato:* `0.00`

```dax
Egresados por Ingresante =
-- La limitacion esta en la descripcion a proposito: la medida es util y
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
    )
```


## 12 Docentes

### `Docentes`

Docentes distintos de pregrado en la serie anual comparable. La fuente repite al docente por cada grado que acredita; el hecho ya cuenta personas distintas.

*Formato:* `#,0`

```dax
Docentes =
-- Mismo tratamiento que [Matriculados], en los dos ejes: el plantel es un
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
    )
```

### `% Docentes Tiempo Completo`

Docentes a tiempo completo o dedicacion exclusiva sobre el total. Condicion Basica de Calidad del licenciamiento SUNEDU.

*Formato:* `0.0%`

```dax
% Docentes Tiempo Completo =
-- Numerador al mismo grano que [Docentes]: serie anual y ultimo anio en
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
    DIVIDE ( Completo, [Docentes] )
```

### `Ratio Alumno Docente`

Matriculados por cada docente, sobre las universidades que reportan las dos fuentes. Se anula si hay filtro de programa o de ubicacion: la fuente de docentes no trae programa ni local, asi que a ese grano el ratio compararia cosas distintas.

*Formato:* `0.0`

```dax
Ratio Alumno Docente =
-- GUARDA DE GRANO, la misma de [Titulados por Egresado] y por el mismo
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
    IF ( FiltroFino, BLANK (), Ratio )
```

### `Ratio Alumno Docente Macrosur`

Ratio alumno/docente del conjunto de universidades con sede en la macrorregion sur, para comparar contra la UCSP.

*Formato:* `0.0`

```dax
Ratio Alumno Docente Macrosur =
-- Se filtra por dim_universidad[es_macrosur_sede] y no por dim_ubicacion,
-- porque fct_docentes no se relaciona con dim_ubicacion. La definicion de
-- universidad del sur es la declarada en dim_universidad: aquella cuya sede
-- principal, por volumen de matricula, esta en la macrorregion sur.
-- Llama a [Ratio Alumno Docente] para heredar su guarda de grano.
CALCULATE (
    [Ratio Alumno Docente],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),
    dim_universidad[es_macrosur_sede] = TRUE
)
```

### `Ratio Alumno Docente Nacional`

Ratio alumno/docente del sistema universitario completo.

*Formato:* `0.0`

```dax
Ratio Alumno Docente Nacional =
-- Llama a [Ratio Alumno Docente] para heredar su guarda de grano.
CALCULATE (
    [Ratio Alumno Docente],
    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] )
)
```


## 13 Narrativa

### `Rango de Anios`

Rango de anios seleccionado, para los titulos de los visuales.

*Formato:* ``

```dax
Rango de Anios =
VAR Desde = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
VAR Hasta = MAXX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )
RETURN
    IF ( Desde = Hasta, FORMAT ( Desde, "0" ), FORMAT ( Desde, "0" ) & "-" & FORMAT ( Hasta, "0" ) )
```

### `Titular Resumen`

Frase de cabecera del resumen ejecutivo y de la pagina 4.1.

*Formato:* ``

```dax
Titular Resumen =
VAR MatU = [CAGR Matricula UCSP]
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
    )
```

### `Titular Demanda`

Frase de cabecera de la pagina 4.2: el programa de mayor y de menor ingreso dentro de los filtros activos.

*Formato:* ``

```dax
Titular Demanda =
VAR Programas =
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
    )
```

### `Titular Tendencia`

Frase de cabecera de la pagina 4.3, con singular y plural resueltos.

*Formato:* ``

```dax
Titular Tendencia =
VAR Conf = [Programas Crecimiento Confirmado]
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
    CONCATENATE ( TxtConf & "; " & TxtCaida & " y " & TxtAlerta, "." )
```

### `Titular Selectividad`

Frase de cabecera de la pagina 4.4: la UCSP frente a sus pares privados. Una diferencia menor a 3 puntos se lee como similar: no se afirma mas de lo que el dato sostiene.

*Formato:* ``

```dax
Titular Selectividad =
VAR U = [Tasa de Admision UCSP]
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
    )
```
