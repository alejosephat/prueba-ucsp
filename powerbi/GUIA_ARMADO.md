# Guía de implementación en Power BI

El **modelo semántico ya está construido** en `UCSP_Benchmark.pbix` y verificado con consultas DAX: 13 tablas, 25 relaciones y 79 medidas. Esta guía cubre lo que falta, la **capa de informe**: tres páginas ejecutivas de 1280 × 720.

La maqueta con cifras reales de cada página está en el dossier (sección 11). Las posiciones de esta guía son las mismas de la maqueta, en píxeles: `x, y, ancho, alto`.

Tiempo estimado: **unos 2 horas**.

---

## 0. El modelo (ya construido)

| Pieza | Cantidad | Dónde está definida |
|---|---|---|
| Tablas | 13, importadas desde `data/gold/*.parquet` | Parámetro de Power Query `RutaGold` |
| Relaciones | 25: 24 uno a muchos y una 1:1 | `powerbi/modelo_tmdl/relationships.tmdl` |
| Medidas | 79, en la tabla `_Medidas`, en 13 carpetas | `05_powerbi.py` → `medidas.csx`, `docs/catalogo_medidas.md` |
| Columna auxiliar | `dim_programa[es_ucsp]` (DAX) | Para el filtro de la página 2 |

**Si se mueve el proyecto de carpeta:** *Transformar datos → Editar parámetros → `RutaGold`* y actualizar.

**Si hay que reconstruir el modelo desde cero:** el modelo completo está como código en `powerbi/modelo_tmdl/` (formato TMDL). Se carga abriendo una carpeta PBIP o con el servidor MCP de Power BI. La otra vía: crear las tablas con el parámetro, las relaciones de abajo y ejecutar `medidas.csx` en Tabular Editor, que crea también `_Medidas` y `es_ucsp`.

### Las relaciones, y por qué faltan algunas

Todas van de la dimensión al hecho, con filtro en una dirección, salvo la 1:1, que Power BI hace bidireccional por definición.

| Dimensión | Hechos relacionados | Hechos sin relación, y por qué |
|---|---|---|
| `dim_periodo[anio]` | los 7 | — |
| `dim_semestre[semestre]` | matrícula, egresados, docentes | Los otros cuatro son anuales en la fuente |
| `dim_universidad[codigo_inei]` | los 7 | — |
| `dim_programa[programa_sk]` | ingresantes, matrícula, postulantes, egresados | Docentes y títulos no traen programa; concentración es por universidad |
| `dim_ubicacion[ubicacion_sk]` | ingresantes, matrícula, postulantes | Egresados trae la geografía **vacía en el 100 %** de las filas |
| `dim_tendencia_programa` ↔ `dim_programa` | 1:1 | — |

Verificado en el modelo: claves únicas en el lado "uno", **cero filas huérfanas** en las 24 relaciones, y una matriz de propagación en la que cada filtro llega exactamente a los hechos de esta tabla.

**No crear** una relación `dim_programa` → `dim_universidad`: abriría una segunda ruta hacia los hechos y Power BI reportaría ambigüedad. Por eso existe `dim_programa[es_ucsp]`.

---

## 1. Tema y lienzo (5 min)

1. *Vista → Temas → Examinar temas* → `powerbi/tema_ucsp_ejecutivo.json`. El tema aplica:
   - la paleta: UCSP en azul `#2A78D6`, sur en pizarra `#5B6573` y país en gris `#A3ACB8`;
   - los bordes de 6 px, el título de visual en Segoe UI Semibold 11 y el fondo de página `#F4F6F9`.
2. Tres páginas, con tamaño de lienzo **16:9 (1280 × 720)**:
   1. *Posición de mercado*
   2. *Portafolio de programas*
   3. *Admisión y selectividad*
3. *Archivo → Opciones → Informe actual*: desactivar *"Permitir que los usuarios cambien el tipo de visual"*.

## 2. Cabecera y filtros (las tres páginas, 20 min)

Se arma en la página 1, se copia y se pega en las otras dos.

| Elemento | Visual | Posición | Contenido |
|---|---|---|---|
| Banda de cabecera | Forma → Rectángulo, blanco, sin borde | 0, 0, 1280, 60 | — |
| Título | Cuadro de texto, Segoe UI Semibold 14 | 16, 4, 620, 30 | Nombre de la página |
| Titular | Tarjeta (nueva), sin etiqueta, 10 pt, alineada a la izquierda | 16, 34, 1000, 22 | `[Titular Resumen]`, `[Titular Tendencia]` o `[Titular Selectividad]` según la página |
| Navegación | *Insertar → Botones → Navegador → Páginas* | 860, 12, 404, 28 | Estilo: botón seleccionado con relleno `#EAF2FC` |
| Fuente | Cuadro de texto, 9 pt, gris | 1000, 74, 264, 22 | `Fuente: SUNEDU · tuni.pe · corte 2025-II` |

**Filtros** (segmentadores desplegables, alto 30, fila `y = 70`):

| Segmentador | Campo | Página 1 | Páginas 2 y 3 |
|---|---|---|---|
| Periodo | `dim_periodo[anio]` | **Entre** (rango), 2021–2025 | **Año**, selección única, 2025 |
| Departamento | `dim_ubicacion[departamento]` | sí | sí |
| Macrorregión | `dim_ubicacion[macrorregion]` | sí | sí |
| Gestión | `dim_universidad[tipo_gestion]` | sí | sí |
| Campo de estudio | `dim_programa[campo_estudio]` | sí | solo página 3 |
| Universidad | `dim_universidad[nombre_universidad]` | — | solo página 2, valor UCSP |

*Ver → Sincronizar segmentaciones*: departamento, macrorregión y gestión en las tres páginas; **Año** solo entre las páginas 2 y 3. El rango de la página 1 no se sincroniza con el año de las otras: la página 1 es una serie y las otras dos son una foto del año.

---

## 3. Página 1 · Posición de mercado (pregunta 4.1, 30 min)

**Titular:** `[Titular Resumen]`.

Las seis fichas y los visuales 9 y 10 llevan el **filtro de visual** `dim_universidad[es_ucsp] = Verdadero`.

| # | Visual | Posición | Campos |
|---|---|---|---|
| 1 | Tarjeta (nueva) · *Matrícula* | 16, 112, 198, 100 | Valor `[Matriculados]`. Etiquetas de referencia: `[Var. Matricula (%)]`, `[CAGR Matricula UCSP]`, `[CAGR Matricula Macrosur]` |
| 2 | Tarjeta (nueva) · *Ingresantes* | 226, 112, 198, 100 | `[Ingresantes Ultimo Anio]`. Referencias: `[Var. Ingresantes (%)]`, `[CAGR Ingresantes UCSP]`, `[CAGR Ingresantes Macrosur]` |
| 3 | Tarjeta (nueva) · *Cuota de la matrícula del sur* | 436, 112, 198, 100 | `[Cuota de Mercado en el Sur]`. Referencia: `[Var. Cuota del Sur (pp)]` |
| 4 | Tarjeta (nueva) · *Programas activos* | 646, 112, 198, 100 | `[Programas Activos]`. Referencia: `[Var. Programas Activos]` |
| 5 | Tarjeta (nueva) · *Concentración (HHI)* | 856, 112, 198, 100 | `[HHI Universidad]`. Referencias: `[Var. HHI]`, `[HHI Mediana Macrosur]` |
| 6 | Tarjeta (nueva) · *Alumnos por docente* | 1066, 112, 198, 100 | `[Ratio Alumno Docente]`. Referencias: `[Ratio Alumno Docente Macrosur]`, `[Ratio Alumno Docente Nacional]` |
| 7 | Gráfico de líneas · *Ingresantes · base 2021 = 100* | 16, 224, 612, 216 | Eje X `dim_periodo[anio]`. Y: `[Indice Ingresantes UCSP]`, `[Indice Ingresantes Macrosur]`, `[Indice Ingresantes Nacional]` |
| 8 | Gráfico de líneas · *Matrícula · base 2021 = 100* | 640, 224, 624, 216 | Eje X `dim_periodo[anio]`. Y: `[Indice Matricula UCSP]`, `[Indice Matricula Macrosur]`, `[Indice Matricula Nacional]` |
| 9 | Barras horizontales · *Matrícula por programa* | 16, 452, 612, 252 | Eje Y `dim_programa[nombre_programa]`, X `[Matriculados]`. Etiqueta de detalle `[% Participacion en su Universidad]`. Orden descendente |
| 10 | Gráfico de líneas · *Cuota de la UCSP en la matrícula del sur* | 640, 452, 624, 252 | Eje X `dim_periodo[anio]`, Y `[Cuota de Mercado en el Sur]`. Etiquetas de datos activadas |

**Formato de las líneas indexadas (7 y 8):**
- La UCSP en azul, de 2,5 px; el sur y el país en gris, de 2 px.
- *Etiquetas de serie* activadas, a la derecha.
- *Analítica → Línea constante* en Y = 100.
- Sin leyenda: las etiquetas de serie la reemplazan.

**Formato de las variaciones en las fichas:** formato condicional de color. Verde `#006300` si es mayor que 0 y rojo `#A32424` si es menor, salvo HHI y programas, que van en gris porque no son buenas ni malas por sí mismas.

## 4. Página 2 · Portafolio de programas (preguntas 4.2 y 4.3, 35 min)

**Titular:** `[Titular Tendencia]`.

**Mitad izquierda: demanda del año (4.2).** Esta mitad responde a los filtros de universidad, departamento, gestión y año, como pide la pregunta.

| # | Visual | Posición | Campos | Filtro de visual |
|---|---|---|---|---|
| 1 | Cuadro de texto + Tarjeta (nueva) | 16, 112, 604, 40 | *Demanda por programa* + `[Titular Demanda]` | — |
| 2 | Barras horizontales · *Mayor ingreso* | 16, 158, 296, 268 | Eje `nombre_programa`, X `[Ingresantes]` | `[Ranking Programa (Ingresantes)]` ≤ 5 |
| 3 | Barras horizontales · *Menor ingreso* | 324, 158, 296, 268 | Eje `nombre_programa`, X `[Ingresantes]`, orden ascendente | `[Ranking Programa Inverso (Ingresantes)]` ≤ 5 |
| 4 | Barras horizontales · *Mayor matrícula* | 16, 436, 296, 268 | Eje `nombre_programa`, X `[Matriculados]` | `[Ranking Programa]` ≤ 5 |
| 5 | Barras horizontales · *Menor matrícula* | 324, 436, 296, 268 | Eje `nombre_programa`, X `[Matriculados]`, orden ascendente | `[Ranking Programa Inverso]` ≤ 5 |

Las barras de mayor van en azul y las de menor en pizarra. Los rankings usan `ALLSELECTED`, así que se recalculan con cada filtro. Los inversos excluyen programas con menos de 10 alumnos, que de otro modo ocuparían siempre el fondo.

**Mitad derecha: tendencia de la UCSP (4.3).** Los visuales 10 y 11 llevan el **filtro de visual** `dim_programa[es_ucsp] = Verdadero`. Sin él, las medidas de tendencia devuelven blanco: usan `SELECTEDVALUE` justamente para no promediar regresiones entre programas.

| # | Visual | Posición | Campos |
|---|---|---|---|
| 6 | Tarjeta · *Crecimiento confirmado* | 636, 112, 148, 52 | `[Programas Crecimiento Confirmado]`, borde izquierdo verde |
| 7 | Tarjeta · *Caída confirmada* | 796, 112, 148, 52 | `[Programas Caida Confirmada]`, borde rojo |
| 8 | Tarjeta · *Alerta: cae el ingreso* | 956, 112, 148, 52 | `[Programas en Alerta]`, borde naranja |
| 9 | Tarjeta · *Programas evaluados* | 1116, 112, 148, 52 | `[Programas Evaluados]` |
| 10 | Dispersión · *Posición frente a su campo en el sur* | 636, 174, 628, 250 | Detalle `nombre_programa`. X `[CAGR Campo Sur Ingresantes]`, Y `[CAGR OLS Ingresantes]`. Tamaño `[Matriculados]`. Leyenda `dim_tendencia_programa[lectura]` |
| 11 | Tabla · *Lectura por programa* | 636, 434, 628, 270 | `nombre_programa`, `[CAGR OLS Ingresantes]`, `[CAGR OLS Matricula]`, `[Delta Ingresantes vs Campo Sur]`, `dim_tendencia_programa[lectura]` |

Las tarjetas 6 a 9 también llevan el filtro `es_ucsp`.

**Dispersión (10):**
- *Analítica → Sombreado de simetría* activado: la diagonal separa los programas que ganan cuota frente a su campo de los que la pierden.
- Líneas constantes en X = 0 y en Y = 0.
- **Colores de la leyenda fijados por lectura**, siempre los mismos:
  - Caída confirmada `#D03B3B`
  - Alerta `#E0702F`
  - Cae la matrícula `#D69A00`
  - Crece la matrícula `#6E7C8F`
  - Sin tendencia `#A3ACB8`
  - Crecimiento confirmado `#0CA30C`

**Tabla (11):**
- Formato condicional de **color de fuente** en las dos columnas de tendencia: gris `#858E9C` cuando `dim_tendencia_programa[p_valor_ing]` (o `[p_valor_mat]`) es mayor o igual a 0,05. Así lo no significativo se ve atenuado.
- `[Delta Ingresantes vs Campo Sur]`: rojo si es menor que 0 y verde si es mayor.
- `lectura`: íconos por regla de valor (▼ rojo, ! naranja, ▽ ámbar, ◆ gris).
- Orden: por lectura y después por tendencia del ingreso.

## 5. Página 3 · Admisión y selectividad (pregunta 4.4, 30 min)

**Titular:** `[Titular Selectividad]`. El segmentador **Año** (sincronizado con la página 2) va en 2025.

| # | Visual | Posición | Campos |
|---|---|---|---|
| 1 | Tarjeta (nueva) · *Tasa de admisión UCSP* | 16, 112, 303, 100 | `[Tasa de Admision UCSP]`. Referencia `[Var. Tasa de Admision UCSP (pp)]` |
| 2 | Tarjeta (nueva) · *Privadas del sur (sin UCSP)* | 331, 112, 303, 100 | `[Tasa de Admision Privadas del Sur]` |
| 3 | Tarjeta (nueva) · *Públicas del sur* | 646, 112, 303, 100 | `[Tasa de Admision Publicas del Sur]` |
| 4 | Tarjeta (nueva) · *Postulaciones UCSP* | 961, 112, 303, 100 | `[Postulaciones]`, referencia `[Var. Postulaciones (%)]`. Filtro de visual `dim_universidad[es_ucsp] = Verdadero` |
| 5 | Gráfico de líneas · *Tasa de admisión* | 16, 224, 612, 228 | Eje X `dim_periodo[anio]`. Y: `[Tasa de Admision UCSP]`, `[Tasa de Admision Privadas del Sur]`, `[Tasa de Admision Publicas del Sur]` |
| 6 | Barras agrupadas horizontales · *Tasa de admisión por campo* | 640, 224, 624, 228 | Eje `dim_programa[campo_estudio]`. X: `[Tasa de Admision UCSP]`, `[Tasa de Admision Privadas del Sur]`. Filtro: `[Tasa de Admision UCSP]` no está en blanco |
| 7 | Embudo · *Embudo de admisión UCSP* | 16, 464, 400, 240 | Valores, sin categoría: `[Postulaciones]`, `[Admitidos]`, `[Ingresantes]`. Filtro de visual `es_ucsp` |
| 8 | Cuadro de texto · *Nota de lectura · 2025* | 428, 464, 200, 240 | El texto de la nota de abajo |
| 9 | Dispersión · *¿Crece captando demanda o bajando la valla?* | 640, 464, 624, 240 | Detalle `nombre_programa`. X `[Tasa de Admision]`, Y `[CAGR OLS Ingresantes]`. Tamaño `[Postulaciones]`. Leyenda `lectura`. Filtro de visual `dim_programa[es_ucsp] = Verdadero` |

**Interacción obligatoria:** *Formato → Editar interacciones*. Desde el segmentador **Año** hacia el visual 5, elegir **Ninguna**. Así la línea muestra 2022–2025 aunque las tarjetas muestren un solo año.

**Dispersión (9):** *Analítica → Línea constante* en el eje X con valor `[Tasa de Admision Privadas del Sur]` (botón fx), etiquetada como "privadas del sur".

**Nota de lectura (texto fijo, vale para 2025):** *"Medicina Humana abre en 2025 con 1,715 postulaciones y admite al 6.4%. Sin ella, la UCSP admite el 79.2% y sus postulaciones caen 12.7%. La caída del agregado es composición, no un cambio de política."*

## 6. Verificación antes de entregar (10 min)

Con los filtros por defecto, estas cifras deben aparecer tal cual. Todas se comprobaron por DAX contra el pipeline.

| Página | Visual | Valor esperado |
|---|---|---|
| 1 | Matrícula / variación / anual / sur | 9,188 · +1.2% · +0.8% · +1.7% |
| 1 | Ingresantes / variación / anual / sur | 2,955 · −3.7% · −4.9% · +8.2% |
| 1 | Cuota del sur / variación | 3.62% · −0.18 pp |
| 1 | HHI / variación / mediana del sur | 1,212 · −49 · 1,340 |
| 1 | Alumnos por docente / sur / país | 16.5 · 15.4 · 19.5 |
| 1 | Índice de ingresantes 2025: UCSP / sur / país | 81.9 · 137.0 · 128.8 |
| 2 | Mayor ingreso / menor ingreso | Ing. Industrial 483 · Contabilidad 65 |
| 2 | Confirmado / caída / alerta / evaluados | 0 · 2 · 1 · 12 |
| 3 | Admisión UCSP / privadas / públicas | 56.4% (−19.9 pp) · 77.4% · 14.1% |
| 3 | Postulaciones UCSP | 5,478 (+27.0%) |

Comprobaciones de comportamiento:

- [ ] Cambiar el departamento a *Arequipa* reordena los cuatro rankings de la página 2.
- [ ] Filtrar la macrorregión *Sur* deja en blanco la ficha de alumnos por docente: es la guarda de grano, porque docentes no tiene geografía.
- [ ] Gestión = *Privado* cambia las series del sur y del país en la página 1: los comparadores respetan la gestión.
- [ ] Quitar el filtro `es_ucsp` de la dispersión de la página 2 deja blancos, no promedios.
- [ ] Ningún visual muestra error ni infinito con un solo año seleccionado.
- [ ] Guardar como `UCSP_Benchmark.pbix` en la raíz del proyecto.
