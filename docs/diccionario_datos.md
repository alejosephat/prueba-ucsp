# Diccionario de datos

Modelo en **esquema estrella**. La estructura de este documento se lee directamente
de la base construida (`data/sunedu.duckdb`) al ejecutar `05_diccionario.py`, de modo
que no puede describir columnas que no existan.

- **Fuente:** datos abiertos de SUNEDU publicados en <https://tuni.pe/datos>
- **Recorte:** ingresantes y matriculados 2021-2025; postulantes 2022-2025
- **Alcance:** solo pregrado (`NIVEL_ACADEMICO = 'Carrera Profesional'`)

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


| Tabla | Tipo | Filas | Granularidad |
|---|---|---|---|
| `dim_periodo` | Dimension | 6 | Una fila por anio. Dimension conformada: se relaciona con los SEIS hechos. El grano es anual porque es el grano comun a todos; el eje semestral vive en dim_semestre. |
| `dim_programa` | Dimension | 2,812 | Una fila por programa de una universidad. |
| `dim_semestre` | Dimension | 3 | Una fila por periodo lectivo: I, II y 'Otro'. Conformada solo sobre los tres hechos semestrales (matricula, egresados, docentes). La fila 'Otro' recoge los periodos de egreso extraordinarios que trae la fuente de egresados. |
| `dim_tendencia_programa` | Dimension | 2,812 | Una fila por programa. Salida del componente estadistico (04_tendencias.py). |
| `dim_ubicacion` | Dimension | 98 | Una fila por combinacion departamento + provincia. |
| `dim_universidad` | Dimension | 168 | Una fila por universidad (codigo INEI). |
| `fct_docentes` | Hecho | 1,300 | Una fila por anio x semestre x universidad. Grano mas grueso que los demas hechos y declarado: la fuente de docentes no trae programa, y su unica geografia es el departamento de NACIMIENTO del docente, no el del local donde ensena. |
| `fct_egresados` | Hecho | 11,000 | Una fila por anio x semestre x universidad x programa. NO tiene ubicacion: medido, DEPARTAMENTO_FILIAL viene vacio en el 100 % de las 587 527 filas de la fuente. |
| `fct_ingresantes` | Hecho | 15,215 | Una fila por anio x universidad x programa x ubicacion. |
| `fct_matricula` | Hecho | 37,828 | Una fila por anio x SEMESTRE x universidad x programa x ubicacion. Estan los 12 semestres de 2020-I a 2025-II; la serie anual comparable se obtiene filtrando dim_semestre[es_serie_anual], que es un filtro de consulta y no un recorte de datos. |
| `fct_postulantes` | Hecho | 10,607 | Una fila por anio x universidad x programa (primera opcion) x ubicacion. |
| `fct_titulos` | Hecho | 915 | Una fila por anio de resolucion x universidad. La universidad se resuelve por igualdad de nombre normalizado porque la fuente no trae codigo INEI (ver control de calidad #11). |

## `dim_periodo`

**Granularidad:** Una fila por anio. Dimension conformada: se relaciona con los SEIS hechos. El grano es anual porque es el grano comun a todos; el eje semestral vive en dim_semestre.

**Llave:** `anio`

**Filas:** 6

| Columna | Tipo | Descripcion |
|---|---|---|
| `anio` | SMALLINT | Anio del periodo academico. FK a dim_periodo. |
| `etiqueta` | VARCHAR | Anio como texto, para etiquetar visuales. |
| `orden` | SMALLINT | Posicion del anio en la serie, para ordenar ejes. |
| `es_ultimo_anio` | BOOLEAN | Marca el ultimo anio disponible, para tarjetas de resumen. |
| `es_tendencia` | BOOLEAN | Marca los anios que entran en la regresion de tendencia (2021-2025). 2020 esta ingestado y visible, pero fuera del test: fue el anio de ruptura por la pandemia (ver el control de calidad #14, que mide cuanto se desvia). |

## `dim_programa`

**Granularidad:** Una fila por programa de una universidad.

**Llave:** `programa_sk  (compuesta: codigo_inei + codigo_siu_programa)`

**Filas:** 2,812

| Columna | Tipo | Descripcion |
|---|---|---|
| `programa_sk` | VARCHAR | Llave sustituta: md5(codigo_inei + '-' + codigo_siu_programa). Es compuesta porque codigo_siu_programa NO es unico a nivel nacional (288 de 471 codigos se repiten). |
| `codigo_inei` | VARCHAR | Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad. |
| `codigo_siu_programa` | VARCHAR | Codigo del programa en el SIU. Unico solo dentro de cada universidad. |
| `nombre_programa` | VARCHAR | Nombre del programa segun la universidad, al valor mas reciente no nulo. |
| `nombre_programa_std` | VARCHAR | Nombre normalizado (mayusculas, sin tildes, espacios colapsados). |
| `codigo_grupo_1` | VARCHAR | Codigo del campo amplio CINE-UNESCO (11 categorias). |
| `nombre_grupo_1` | VARCHAR | Campo amplio de estudio CINE-UNESCO. |
| `codigo_grupo_3` | VARCHAR | Codigo del campo detallado CINE-UNESCO (83 categorias). |
| `nombre_grupo_3` | VARCHAR | Campo detallado CINE-UNESCO. **Criterio de homologacion** entre universidades. |
| `campo_estudio` | VARCHAR | nombre_grupo_3, o 'Sin clasificar CINE' cuando la fuente no lo reporta. Usar este campo en los visuales para que los no clasificados sigan siendo visibles. |
| `nivel_academico` | VARCHAR | Nivel del programa. El modelo contiene solo 'Carrera Profesional' (pregrado). |

## `dim_semestre`

**Granularidad:** Una fila por periodo lectivo: I, II y 'Otro'. Conformada solo sobre los tres hechos semestrales (matricula, egresados, docentes). La fila 'Otro' recoge los periodos de egreso extraordinarios que trae la fuente de egresados.

**Llave:** `semestre`

**Filas:** 3

| Columna | Tipo | Descripcion |
|---|---|---|
| `semestre` | INTEGER | Periodo lectivo dentro del anio: 1, 2, o 0 para los periodos extraordinarios. FK a dim_semestre. |
| `etiqueta` | VARCHAR | Anio como texto, para etiquetar visuales. |
| `es_serie_anual` | BOOLEAN | Marca el semestre que define la serie anual comparable. Las medidas de matricula y de docentes filtran por este atributo en vez de por un literal, para que no haya dos verdades entre config.py y el modelo. |

## `dim_tendencia_programa`

**Granularidad:** Una fila por programa. Salida del componente estadistico (04_tendencias.py).

**Llave:** `programa_sk`

**Filas:** 2,812

| Columna | Tipo | Descripcion |
|---|---|---|
| `programa_sk` | VARCHAR | Llave sustituta: md5(codigo_inei + '-' + codigo_siu_programa). Es compuesta porque codigo_siu_programa NO es unico a nivel nacional (288 de 471 codigos se repiten). |
| `anios_ing` | INTEGER | Anios con ingresantes positiva en 2021-2025 que entran en la regresion. |
| `cagr_ing` | DOUBLE | CAGR de ingresantes estimado por OLS sobre log(ingresantes) 2021-2025. |
| `p_valor_ing` | DOUBLE | p-valor del t-test de la pendiente de ingresantes (gl = n - 2). |
| `tendencia_ing` | VARCHAR | Crecimiento sostenido / Caida sostenida / Sin tendencia sostenida / Serie insuficiente. |
| `ingresantes_ultimo_anio` | INTEGER | Ingresantes del ultimo anio de la ventana, para dimensionar el programa. |
| `cagr_campo_sur_ing` | DOUBLE | CAGR OLS de ingresantes del mismo campo CINE en la macrorregion sur, SIN la UCSP. |
| `delta_campo_sur_ing` | DOUBLE | cagr_ing menos cagr_campo_sur_ing. Positivo = el programa gana cuota en el sur. |
| `cuadrante_ing` | VARCHAR | Posicion de ingresantes frente a su campo en el sur: gana/pierde cuota, crece o cae con el campo. |
| `anios_mat` | INTEGER | Anios con matricula positiva en 2021-2025 que entran en la regresion. |
| `cagr_mat` | DOUBLE | CAGR de matricula estimado por OLS sobre log(matriculados) 2021-2025. |
| `p_valor_mat` | DOUBLE | p-valor del t-test de la pendiente de matricula (gl = n - 2). |
| `tendencia_mat` | VARCHAR | Crecimiento sostenido / Caida sostenida / Sin tendencia sostenida / Serie insuficiente. |
| `matriculados_ultimo_anio` | INTEGER | Matriculados del ultimo anio de la ventana, para dimensionar el programa. |
| `cagr_campo_sur_mat` | DOUBLE | CAGR OLS de matricula del mismo campo CINE en la macrorregion sur, SIN la UCSP. |
| `delta_campo_sur_mat` | DOUBLE | cagr_mat menos cagr_campo_sur_mat. Positivo = el programa gana cuota en el sur. |
| `cuadrante_mat` | VARCHAR | Posicion de matricula frente a su campo en el sur: gana/pierde cuota, crece o cae con el campo. |
| `lectura` | VARCHAR | Cruce de las dos series: crecimiento o caida confirmada, alerta (cae el ingreso y la matricula aun no), o la matricula se mueve sin el ingreso. |

## `dim_ubicacion`

**Granularidad:** Una fila por combinacion departamento + provincia.

**Llave:** `ubicacion_sk  (compuesta: departamento + provincia)`

**Filas:** 98

| Columna | Tipo | Descripcion |
|---|---|---|
| `ubicacion_sk` | VARCHAR | Llave sustituta de la ubicacion. FK a dim_ubicacion. |
| `departamento` | VARCHAR | Departamento del local o filial donde se dicta el programa. **Filtro obligatorio**. |
| `provincia` | VARCHAR | Provincia del local o filial. |
| `macrorregion` | VARCHAR | Norte, Centro, Sur u Oriente. Definido en referencias/macrorregiones.csv. |
| `es_macrosur` | BOOLEAN | Marca la macrorregion sur. **Filtro obligatorio** del enunciado. |

## `dim_universidad`

**Granularidad:** Una fila por universidad (codigo INEI).

**Llave:** `codigo_inei`

**Filas:** 168

| Columna | Tipo | Descripcion |
|---|---|---|
| `codigo_inei` | VARCHAR | Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad. |
| `nombre_universidad` | VARCHAR | Nombre de la universidad, resuelto al valor mas reciente no nulo. |
| `tipo_entidad` | VARCHAR | Universidad, Escuela de Posgrado, Escuela Superior o Instituto. |
| `tipo_gestion` | VARCHAR | Publico o Privado. **Filtro obligatorio** del enunciado. |
| `tipo_constitucion` | VARCHAR | Publica, Privada asociativa o Privada societaria. |
| `licenciamiento` | VARCHAR | Estado de licenciamiento institucional ante SUNEDU. |
| `departamento_sede` | VARCHAR | Departamento donde la universidad concentra MAS matricula. Define su sede principal. |
| `macrorregion_sede` | VARCHAR | Macrorregion de la sede principal. Clasifica a la universidad entera. |
| `es_macrosur_sede` | BOOLEAN | Marca las universidades con sede principal en el sur. **Distinto de dim_ubicacion[es_macrosur]**, que marca donde se imparte un programa: una universidad de Lima con filial en Cusco aporta matricula al sur pero no es una universidad del sur. |
| `es_ucsp` | BOOLEAN | Marca la Universidad Catolica San Pablo (codigo INEI 260000062). |

## `fct_docentes`

**Granularidad:** Una fila por anio x semestre x universidad. Grano mas grueso que los demas hechos y declarado: la fuente de docentes no trae programa, y su unica geografia es el departamento de NACIMIENTO del docente, no el del local donde ensena.

**Llave:** `anio + semestre + codigo_inei`

**Filas:** 1,300

| Columna | Tipo | Descripcion |
|---|---|---|
| `anio` | SMALLINT | Anio del periodo academico. FK a dim_periodo. |
| `semestre` | TINYINT | Periodo lectivo dentro del anio: 1, 2, o 0 para los periodos extraordinarios. FK a dim_semestre. |
| `codigo_inei` | VARCHAR | Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad. |
| `docentes` | BIGINT | Docentes distintos de pregrado en la universidad y el semestre. La fuente repite al docente una vez por cada grado que acredita, de ahi el conteo de personas distintas. |
| `docentes_tiempo_completo` | BIGINT | Docentes a tiempo completo o dedicacion exclusiva. Insumo del porcentaje que SUNEDU exige como Condicion Basica de Calidad. |
| `docentes_posgrado` | BIGINT | Docentes con grado de maestro o doctor. |
| `docentes_ordinarios` | BIGINT | Docentes en condicion de ordinarios (de carrera), frente a contratados. |

## `fct_egresados`

**Granularidad:** Una fila por anio x semestre x universidad x programa. NO tiene ubicacion: medido, DEPARTAMENTO_FILIAL viene vacio en el 100 % de las 587 527 filas de la fuente.

**Llave:** `anio + semestre + programa_sk`

**Filas:** 11,000

| Columna | Tipo | Descripcion |
|---|---|---|
| `anio` | SMALLINT | Anio del periodo academico. FK a dim_periodo. |
| `semestre` | TINYINT | Periodo lectivo dentro del anio: 1, 2, o 0 para los periodos extraordinarios. FK a dim_semestre. |
| `codigo_inei` | VARCHAR | Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad. |
| `programa_sk` | VARCHAR | Llave sustituta: md5(codigo_inei + '-' + codigo_siu_programa). Es compuesta porque codigo_siu_programa NO es unico a nivel nacional (288 de 471 codigos se repiten). |
| `egresados` | BIGINT | Personas distintas que egresan (terminan los cursos) del programa en el periodo. Egresar es un FLUJO, asi que sumar los dos semestres de un anio es correcto -- a diferencia de la matricula, que es un stock y se duplicaria. |
| `nota_promedio` | DOUBLE | Nota promedio de los egresados del grupo. Al agregarla hay que reponderarla por numero de egresados: promediar promedios de grupos de distinto tamano da un numero que no corresponde a ningun alumno. |
| `creditos_aprobados` | DOUBLE | Creditos aprobados al egresar, promedio del grupo. |

## `fct_ingresantes`

**Granularidad:** Una fila por anio x universidad x programa x ubicacion.

**Llave:** `anio + programa_sk + ubicacion_sk`

**Filas:** 15,215

| Columna | Tipo | Descripcion |
|---|---|---|
| `anio` | SMALLINT | Anio del periodo academico. FK a dim_periodo. |
| `codigo_inei` | VARCHAR | Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad. |
| `programa_sk` | VARCHAR | Llave sustituta: md5(codigo_inei + '-' + codigo_siu_programa). Es compuesta porque codigo_siu_programa NO es unico a nivel nacional (288 de 471 codigos se repiten). |
| `ubicacion_sk` | VARCHAR | Llave sustituta de la ubicacion. FK a dim_ubicacion. |
| `ingresantes` | BIGINT | Personas distintas que ingresan al programa ese anio. |

## `fct_matricula`

**Granularidad:** Una fila por anio x SEMESTRE x universidad x programa x ubicacion. Estan los 12 semestres de 2020-I a 2025-II; la serie anual comparable se obtiene filtrando dim_semestre[es_serie_anual], que es un filtro de consulta y no un recorte de datos.

**Llave:** `anio + semestre + programa_sk + ubicacion_sk`

**Filas:** 37,828

| Columna | Tipo | Descripcion |
|---|---|---|
| `anio` | SMALLINT | Anio del periodo academico. FK a dim_periodo. |
| `semestre` | TINYINT | Periodo lectivo dentro del anio: 1, 2, o 0 para los periodos extraordinarios. FK a dim_semestre. |
| `codigo_inei` | VARCHAR | Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad. |
| `programa_sk` | VARCHAR | Llave sustituta: md5(codigo_inei + '-' + codigo_siu_programa). Es compuesta porque codigo_siu_programa NO es unico a nivel nacional (288 de 471 codigos se repiten). |
| `ubicacion_sk` | VARCHAR | Llave sustituta de la ubicacion. FK a dim_ubicacion. |
| `matriculados` | BIGINT | Personas distintas matriculadas en el programa en el periodo I del anio. |

## `fct_postulantes`

**Granularidad:** Una fila por anio x universidad x programa (primera opcion) x ubicacion.

**Llave:** `anio + programa_sk + ubicacion_sk`

**Filas:** 10,607

| Columna | Tipo | Descripcion |
|---|---|---|
| `anio` | SMALLINT | Anio del periodo academico. FK a dim_periodo. |
| `codigo_inei` | VARCHAR | Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad. |
| `programa_sk` | VARCHAR | Llave sustituta: md5(codigo_inei + '-' + codigo_siu_programa). Es compuesta porque codigo_siu_programa NO es unico a nivel nacional (288 de 471 codigos se repiten). |
| `ubicacion_sk` | VARCHAR | Llave sustituta de la ubicacion. FK a dim_ubicacion. |
| `postulaciones` | BIGINT | Postulaciones recibidas. Una persona puede postular a varios programas. |
| `postulantes` | BIGINT | Personas distintas que postulan al programa como primera opcion. |
| `admitidos` | BIGINT | Postulaciones con ES_INGRESANTE = SI en la fuente. Numerador de la tasa de admision. |

## `fct_titulos`

**Granularidad:** Una fila por anio de resolucion x universidad. La universidad se resuelve por igualdad de nombre normalizado porque la fuente no trae codigo INEI (ver control de calidad #11).

**Llave:** `anio + codigo_inei`

**Filas:** 915

| Columna | Tipo | Descripcion |
|---|---|---|
| `anio` | SMALLINT | Anio del periodo academico. FK a dim_periodo. |
| `codigo_inei` | VARCHAR | Codigo INEI de la universidad. Llave estable entre periodos. FK a dim_universidad. |
| `titulos` | BIGINT | EVENTOS de titulacion con resolucion en el anio: grados de bachiller y titulos profesionales. Titulacion EFECTIVA (obtener el diploma), que no es lo mismo que egreso (terminar los cursos). NO es un conteo de personas: medido, 437 872 personas tienen dos titulos (el grado y el titulo) y 4 153 tienen tres o mas. |
| `personas` | BIGINT | Personas distintas tituladas en el anio. Es la cifra comparable con un conteo de egresados; `titulos` no lo es, porque cuenta eventos. |
| `bachilleres` | BIGINT | De los anteriores, los que son grado de bachiller. |
| `titulados` | BIGINT | De los anteriores, los que son titulo profesional. |
| `anios_estudio_mediana` | DECIMAL(5,2) | Mediana de anios entre matricula y egreso, calculada sobre las fechas que trae la propia fuente de grados y titulos. Mide duracion real de estudios. |
