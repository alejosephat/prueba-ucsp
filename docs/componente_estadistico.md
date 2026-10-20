# Componente estadístico — regresión de tendencia

**Técnica:** regresión lineal simple (OLS) de `log(y)` contra el año, 2021–2025, **por programa** y sobre **dos series**: ingresantes y matrícula. La pendiente es la tasa de crecimiento anual compuesta (CAGR); el p-valor dice si esa pendiente se distingue del azar.

**Para qué:** responder la pregunta 4.3 —qué programas de la UCSP tienen una tendencia *sostenida* y cómo se compara con sus equivalentes del sur— con un criterio explícito y reproducible, en vez de mirar una línea y opinar.

Código: [`04_tendencias.py`](../04_tendencias.py) · salida: `dim_tendencia_programa` · medidas: carpeta `09 Tendencia` · dashboard: página 3.

---

## 1. Por qué una regresión, y no otra de las técnicas sugeridas

| Alternativa | Qué entrega | Por qué no es la técnica principal |
|---|---|---|
| CAGR punta a punta (`[CAGR Matricula]`) | crecimiento entre dos años | Usa 2 de los 5 puntos: un año atípico en un extremo cambia el signo. No dice si el cambio es *sostenido*. Se mantiene como medida DAX, porque responde al rango que elige el usuario. |
| Clasificación por crecimiento | grupos de programas | Necesita un criterio de "sostenido". La regresión **es** ese criterio: la clasificación se construye sobre ella. |
| Índice de concentración (HHI) | reparto de la matrícula | No habla de tendencia. Tampoco se usa como indicador: la distribución se lee mejor en barras de participación. |
| Proyección simple | valor futuro | Con 5 puntos y sin modelo causal, proyectar es extrapolar ruido. La 4.3 pregunta por la tendencia observada, no por el futuro. |
| Mann-Kendall (no paramétrico) | tendencia monótona, sin suponer normalidad | Con n = 5 solo declara significativa una serie **perfectamente** monótona (p mínimo = 2/120 = 0,017; con una sola inversión ya es 0,083), y no entrega la magnitud. |

La regresión en logaritmo es la única de la lista que da a la vez **magnitud** (CAGR), **incertidumbre** (p-valor) y **comparabilidad** entre programas de tamaños distintos.

## 2. Cómo funciona

```
log(y_t) = a + b·t + e_t        CAGR = e^b − 1        t = b / ee(b),  gl = n − 2
```

- **Por qué logaritmo.** La pendiente queda en tasa, no en alumnos. Un programa que pasa de 80 a 120 y otro que pasa de 800 a 1 200 tienen la misma pendiente. En niveles, el grande ganaría siempre.
- **Benchmark de la 4.3.** La misma regresión se aplica a la serie agregada del **mismo campo CINE** (nivel 3, la clasificación que SUNEDU ya trae en la fuente) en la macrorregión sur, **excluyendo a la UCSP**. La diferencia entre ambos CAGR dice si el programa gana o pierde cuota en su mercado.
- **Ventana 2021–2025.** 2020 está en el modelo pero fuera del test: su rebote post-pandemia (+10,7 % nacional, control #14) arrastraría la pendiente de casi todos los programas.

## 3. Por qué dos series y no solo matrícula

La matrícula es un **stock**: acumula cohortes. Un programa abierto en 2020 llena sus cinco años de alumnos aunque su ingreso caiga, y la regresión de matrícula sola lo reporta como crecimiento. Medido en la UCSP:

| Programa | Ingresantes 2021 → 2025 | CAGR ingreso | Matrícula 2021 → 2025 | CAGR matrícula |
|---|---|---|---|---|
| Arquitectura y Urbanismo | 261 → 217 | **−4,1 %** (p = 0,012) | 214 → 607 | **+29,8 %** (p = 0,002) |
| Ingeniería Mecatrónica | 178 → 192 | +2,5 % (p = 0,43) | 137 → 378 | +28,0 % (p = 0,001) |
| Ingeniería Ambiental | 195 → 101 | −12,6 % (p = 0,10) | 98 → 229 | +23,4 % (p = 0,003) |

Con una sola serie, los tres serían "crecimiento sostenido". Arquitectura, de hecho, **pierde demanda**. El ingreso es el indicador **adelantado**; la matrícula lo confirma con rezago. La 4.3 pide las dos, y la lectura cruzada las combina:

| Ingreso | Matrícula | Lectura |
|---|---|---|
| crece | crece | **Crecimiento confirmado** |
| crece | no crece | Ingreso en alza (aún no llega a la matrícula) |
| cae | cae | **Caída confirmada** |
| cae | no cae | **Alerta: cae el ingreso** |
| sin tendencia | crece | Crece la matrícula, no el ingreso (cohortes que se acumulan o mejor retención) |
| sin tendencia | cae | Cae la matrícula, no el ingreso (egreso de cohortes grandes o deserción) |
| sin tendencia | sin tendencia | Sin tendencia sostenida |

## 4. Definición de "tendencia sostenida"

Tres condiciones **a la vez**, sobre cada serie:

| Condición | Por qué |
|---|---|
| **≥ 4 años con dato** | Con 3 puntos queda 1 grado de libertad y el t crítico es 12,7: el test no puede detectar nada. |
| **p < 0,05** | La pendiente no es atribuible al azar. Con 5 puntos exige \|t\| > 3,18. |
| **\|CAGR\| ≥ 3 %** | Materialidad. Con muchos años muy estables, una pendiente de +1 % puede salir significativa sin que cambie ninguna decisión. 3 % anual acumula ~13 % en la ventana. Es un parámetro declarado, no un resultado: `CAGR_MIN` en `config.py`. |

Todo lo que no cumple las tres es **"sin tendencia sostenida"**. No se separa "estable" de "irregular": con cinco puntos esa distinción exige un tercer umbral sobre la dispersión, y medido, el **57 %** de los ingresos con pendiente plana oscila más de un 10 % alrededor de ella. Llamarlos "estables" sería afirmar más de lo que el dato permite.

**No se usa el R².** Mide qué parte de la variación explica la pendiente, y en una serie plana es ~0 por construcción, por estable que sea. Usarlo para distinguir "estable" de "volátil" etiqueta como volátiles justo a las series más quietas.

## 5. Condiciones de aplicabilidad

| Supuesto de OLS | ¿Se cumple aquí? | Cómo se trató |
|---|---|---|
| Relación lineal en log (tasa constante) | Razonable en 5 años. Falla con quiebres: apertura o cierre de un programa, licencia denegada. | Ventana sin el quiebre de 2020; series con menos de 4 años quedan fuera. |
| Residuos independientes | **No en la matrícula**: los mismos alumnos están año tras año, así que los errores se arrastran y el p-valor sale optimista. Aproximadamente sí en el ingreso, que es una cohorte nueva cada año. | Por eso en la lectura cruzada **manda el ingreso**. |
| Normalidad y varianza constante | No verificable con 5 puntos. | El p-valor se lee como indicativo, no como prueba formal. |
| Valores positivos | El logaritmo no admite 0. | Un año sin dato se trata como ausente; con menos de 4 años, "serie insuficiente". |

## 6. Limitaciones

1. **Poca potencia.** Con 3 grados de libertad, el intervalo de confianza del CAGR mide en la mediana **39 puntos** de ancho en ingresantes y **14** en matrícula. "Sin tendencia sostenida" significa *no demostrada*, no *estable*.
2. **Comparaciones múltiples.** Se estiman 4 051 regresiones (1 831 de ingreso y 2 220 de matrícula: las series con 4 años o más). Al 5 %, si ningún programa tuviera tendencia, ~5 % saldrían significativos por azar. En la UCSP son 24 pruebas: cabe esperar ~1 falso positivo. Exigir las **dos** series para hablar de crecimiento o caída *confirmados* reduce ese riesgo.
3. **El sistema también crece.** La matrícula nacional creció entre 3,0 % y 7,7 % al año en la ventana (control #14). Un programa a +3 % puede estar perdiendo cuota: por eso la tendencia absoluta se lee junto al **delta contra su campo en el sur**.
4. **Homologación.** El benchmark agrega por campo CINE. ~20 % de los registros del sistema no traen campo y quedan fuera del comparador; los 13 programas de la UCSP sí lo tienen.
5. **2021 sigue siendo un año de pandemia**, y una tendencia histórica no es una causa ni un pronóstico.

## 7. Resultado en la UCSP

| Lectura | Programas |
|---|---|
| Caída confirmada | Contabilidad · Administración de Negocios |
| **Alerta: cae el ingreso** | **Arquitectura y Urbanismo** |
| Crece la matrícula, no el ingreso | Ingeniería Ambiental · Ingeniería Mecatrónica · Psicología · Ciencia de la Computación |
| Cae la matrícula, no el ingreso | Ingeniería Electrónica y de Telecomunicaciones · Ingeniería Industrial |
| Sin tendencia sostenida | Derecho · Ingeniería Civil · Educación |
| Serie insuficiente | Medicina Humana (abre en 2025) |

Ningún programa de la UCSP tiene crecimiento **confirmado** en las dos series. En el sistema completo, 104 de 2 812.
