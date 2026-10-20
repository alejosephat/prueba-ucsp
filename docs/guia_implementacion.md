# Guía de implementación y desarrollo

Cómo se construyó este proyecto: el orden en que se hicieron las cosas, por qué en ese orden, qué decisiones se tomaron en la planificación y qué obligó a cambiar el plan sobre la marcha.

Es un complemento de [`decisiones_tecnicas.md`](decisiones_tecnicas.md), que registra el *qué* y el *por qué* de cada decisión. Este documento registra el *cómo se llegó* a ellas.

---

## 1. Cómo se leyó el enunciado

Antes de escribir una línea, se desglosó la rúbrica de evaluación, porque determina dónde conviene invertir el esfuerzo:

| Criterio | Peso | Lectura |
|---|---|---|
| Ingesta y transformación | 20 % | El más alto. "Reproducible, sin pasos manuales" es verificable: o corre de punta a punta, o no. |
| Modelo de datos | 20 % | Esquema estrella, granularidad declarada, dimensiones conformadas. |
| Calidad e integración | 15 % | Pide controles **con resultados reportados**, no solo implementados. |
| Medidas DAX | 15 % | Cuatro medidas obligatorias, y "buenas prácticas" explícitamente nombradas. |
| Análisis y respuestas | 15 % | Incluye el componente estadístico y la pregunta adicional. |
| Dashboard | 10 % | El entregable más visible, pero el de menor peso. |
| Documentación | 5 % | Poco peso, pero barato de obtener bien. |

**Conclusión que orientó todo el plan:** el 70 % del puntaje está en *cómo se construye*, no en los hallazgos. El enunciado lo refuerza al decir que la PPT "no es una PPT de hallazgos". Por eso el esfuerzo se concentró en el pipeline, el modelo y la trazabilidad, y el dashboard se dejó como el último paso.

Tres frases del enunciado se tomaron literalmente y condicionaron el diseño:

- *"sin pasos manuales"* → obligó a automatizar la descarga, que resultó ser lo más difícil del proyecto.
- *"se valorará especialmente SQL"* → la lógica va en archivos `.sql`, no embebida en pandas.
- *"No buscamos cubrirlo todo. Se valora la capacidad de enfocarte, acotar y priorizar"* → permiso explícito para dejar cosas fuera, siempre que se declaren.

---

## 2. Decisiones de planificación

Tomadas antes de escribir código, y todas revisables.

### 2.1 Explorar la fuente antes de planificar

La primera decisión fue **no planificar sobre supuestos**. Antes de proponer una arquitectura se descargaron y perfilaron archivos reales. Costó cerca de una hora y evitó tres errores que habrían sido caros de descubrir tarde:

1. Que `CODIGO_SIU_PROGRAMA` no es único a nivel nacional (habría corrompido el modelo entero en silencio).
2. Que la fuente ya trae la clasificación CINE (habría llevado a implementar fuzzy matching innecesario).
3. Que el volumen descomprimido es de varios GB —5,4 en el alcance final, ~7 en el plan inicial— y que eso descartaba un diseño en pandas que no cabe en memoria.

**Regla aplicada:** en un proyecto con fuente desconocida, el perfilado va antes del diseño, no después.

### 2.2 Acotar el alcance de forma declarada

El enunciado permite acotar. Se acotó en cuatro ejes, y cada recorte se declaró con su justificación:

| Eje | Decisión | Razón |
|---|---|---|
| Temporal | 2021–2025 | Cinco puntos es el mínimo para un test de tendencia con sentido (gl = 3), y deja fuera 2020 |
| Nivel | Solo pregrado | El enunciado lo pide explícitamente |
| Semestral | Periodo I de cada año | Las cuatro preguntas son anuales; el sesgo se midió (−2,81 %) |
| Fuentes | Ingresantes + matriculados + postulantes | Las dos obligatorias más una adicional; se dejaron fuera egresados, docentes y GYT |

**El criterio general fue: es mejor hacer bien tres fuentes que a medias seis.**

### 2.3 Ruta crítica y orden de construcción

Dos cosas no se podían paralelizar ni acelerar: la descarga de ~590 MB y el ensamblado manual del `.pbix`. Todo el cronograma se organizó alrededor de eso:

```
descarga  ──► transformación ──► gold ──► medidas DAX ──► .pbix (manual)
    │                                          │
    │  (mientras descarga: escribir el SQL)    │  (mientras: documentación y PPT)
```

**Consecuencia práctica:** la descarga se lanzó en segundo plano en el primer minuto de la implementación, y el SQL de silver y gold se escribió mientras corría. El mismo patrón se repitió con la transformación de 8 minutos.

### 2.4 Separar lo que automatiza una máquina de lo que no

Power BI Desktop es una aplicación de escritorio: el `.pbix` no se puede generar desde fuera. En vez de dejarlo como un hueco, se decidió **reducir el trabajo manual al mínimo irreductible**:

- las tablas se entregan como Parquet listos para cargar;
- las 79 medidas se crean con un clic mediante un script de Tabular Editor;
- las 25 relaciones vienen en una tabla, una por fila;
- una tabla de verificación de cinco cifras permite confirmar que el montaje quedó bien.

Lo que queda manual es cargar, relacionar y componer los visuales: entre 60 y 90 minutos.

### 2.5 Escribir el código para que sobreviva al cambio de motor

Se asumió desde el principio que DuckDB es el motor *de este ejercicio*, no de la institución. Por eso la estructura separa `sql/bronze/` (específico del motor) de `sql/silver/` y `sql/gold/` (portables, con las salvedades medidas en `sql/portabilidad.md`), y Python nunca contiene lógica de negocio. La decisión costó poco en el momento y es lo que permite sostener, en la sustentación, que la solución se traslada a SQL Server o a Fabric con un trabajo de traducción acotado y medido, no reescribiéndose.

### 2.6 Principio rector del código

**El código de cada etapa debe ser lo más simple posible para cumplir la tarea.** En concreto: sin framework ni clases, scripts numerados que se leen de arriba a abajo, una sola dependencia nueva (`duckdb`), y cero fuzzy matching porque la fuente ya trae las llaves.

Esto se aplicó también al descartar cosas tentadoras: no hay sistema de logging, ni configuración en YAML, ni tests unitarios, ni orquestador. Para un pipeline de siete scripts que corre en nueve minutos, cualquiera de esos añadidos cuesta más de lo que aporta.

---

## 3. Fases de construcción

### Fase 0 — Exploración de la fuente (~1 h)

`tuni.pe/datos` resultó ser una SPA de Angular sin URLs de descarga visibles. La secuencia de diagnóstico fue:

1. `curl` a la página → solo el esqueleto HTML, sin contenido.
2. `configs/config.js` → reveló la URL base de la API.
3. El bundle `main.js` → los servicios de Angular y sus endpoints.
4. El chunk perezoso `pages-info-datos-info-datos-module.js` → la lógica del botón de descarga.
5. Llamadas directas a la API hasta reproducir la cadena completa.

Después se descargaron tres archivos reales y se perfilaron con pandas y DuckDB: encoding, delimitador, nulos, cardinalidades, unicidad de llaves.

**Qué salió de aquí:** la cadena de cinco pasos de la ingesta, los tres hallazgos que definieron el modelo, y la certeza de que el volumen obligaba a procesar por lotes.

### Fase 1 — Plan, y su primera corrección

El plan inicial proponía descargar los 12 semestres de matrícula y descomprimirlos todos: **23 archivos, 900 MB comprimidos, ~7 GB de pico de disco.**

Al revisarlo, ese volumen era desproporcionado para el ejercicio. El plan se corrigió con tres cambios:

| | Plan inicial | Plan corregido |
|---|---|---|
| Archivos | 23 | 16 |
| Descarga | ~900 MB | ~590 MB |
| Pico de disco | ~7 GB | **601 MB** |

Los tres cambios: serie de cinco años en vez de seis, matrícula solo del periodo I, y procesar un archivo a la vez en vez de descomprimirlos todos.

**Lección:** el pico de disco era un error de diseño, no una necesidad del problema. Procesar en bucle —descomprimir, agregar, borrar— no pierde un solo dato y reduce la huella en un 90 %.

### Fase 2 — Ingesta (`01_descargar.py`)

Lo más difícil del proyecto, por dos obstáculos que no se anticipan leyendo documentación:

- **El paso de listado es obligatorio.** Pedir el archivo directamente devuelve `403`; hay que listar la carpeta de SharePoint antes. Se descubrió comparando una secuencia de `curl` que funcionaba contra una de `requests` que no.
- **El header `Origin` rompe SharePoint.** La primera versión lo ponía en la sesión completa, y SharePoint lo rechazaba con `403`. La solución es aplicarlo solo a las llamadas a la API de TUNI.

Una vez resuelto, se añadió el manifiesto con `sha256` para que la reejecución fuera idempotente.

**Verificación:** se probó resolver tres archivos distintos en la misma sesión antes de lanzar la descarga completa. Ese paso de diez segundos evitó descubrir un fallo a mitad de 590 MB.

### Fase 3 — Transformación (`02_transformar.py` + `sql/`)

Python se limitó a abrir DuckDB, recorrer los zips y ejecutar los `.sql` en orden. Dos tropiezos:

- **El encoding.** DuckDB rechazó `latin-1`. Contando bytes por rango aparecieron 71 ocurrencias de `0x96`, indefinido en ISO-8859-1: los archivos son **cp1252**. Se resolvió con la extensión `encodings`.
- **El export a Parquet no encontraba las tablas.** El `LIKE 'dim\_%' ESCAPE '\'` sobre `information_schema` no matcheaba. Se cambió por `duckdb_tables()` con un `LIKE` simple. La lección es la de siempre: cuando una consulta no devuelve filas, simplificarla antes de depurarla.

También se añadió un flag `--solo-gold` para reconstruir el modelo sin releer los CSV. Costó tres líneas y ahorró varias iteraciones de ocho minutos cada una.

### Fase 4 — Modelo dimensional (`sql/gold/`)

Aquí ocurrió la corrección de mayor impacto analítico. La primera versión de `dim_programa` resolvía los atributos divergentes tomando **la fila completa del año más reciente**:

```sql
row_number() OVER (PARTITION BY ... ORDER BY anio DESC)
```

El control de calidad de nulos reveló que 415 de 2 733 programas quedaban sin clasificación CINE. Al investigar, muchos la tenían en años anteriores y vacía en el último. Se cambió a tomar, **para cada atributo por separado**, su valor más reciente no nulo:

```sql
max_by(nombre_grupo_3, anio) FILTER (WHERE nombre_grupo_3 IS NOT NULL)
```

Los programas sin campo CINE bajaron de 415 a 225 —190 recuperados— sin inventar un solo dato.

**Lección:** el control de calidad no solo detecta errores; cuando se lee con atención, sugiere mejoras al modelo. Esta no se habría encontrado sin el control 04.

### Fase 5 — Calidad (`sql/calidad.sql`)

Se escribieron 17 controles en una sola consulta con `UNION ALL`, devolviendo un resultset uniforme. La decisión de hacerlo todo en SQL —en vez de un script de Python con asserts— permite pegarlo tal cual en el SQL Endpoint de Fabric o en SSMS.

El control 09 **no estaba en el plan**: surgió al descubrir que el dataset de postulantes trae `ES_INGRESANTE`. Comparar esos admitidos contra el dataset de ingresantes enfrenta dos sistemas de reporte independientes de SUNEDU. Concuerdan dentro del 3 %, y es probablemente la evidencia más fuerte del proyecto.

### Fase 6 — Estadística (`04_tendencias.py`)

Se eligió OLS sobre `log(matriculados)` porque la pendiente en logaritmo *es* la tasa de crecimiento compuesta, lo que hace comparables programas de tamaños muy distintos.

Se planificó calcular el p-valor con fórmulas cerradas para no añadir dependencias, pero al verificar el entorno `scipy` ya estaba instalado: una línea en vez de treinta.

El benchmark sectorial —el CAGR del mismo campo CINE en el sur, excluyendo a la UCSP— se añadió al darse cuenta de que sin él la comparación de la pregunta 4.3 no distingue "el campo entero cae" de "esta universidad pierde cuota".

### Fase 7 — Capa semántica y documentación

Para evitar que el catálogo de medidas y el modelo se desincronizaran, se definieron las medidas **una sola vez** en una lista de Python, que genera el script de Tabular Editor, el respaldo en texto plano y el catálogo documentado. El mismo principio se aplicó al diccionario de datos, que se genera leyendo el esquema real de la base.

**Regla aplicada:** si un documento describe algo que el código ya sabe, que lo genere el código.

### Fase 8 — Presentación

La primera versión era legible pero genérica: paleta azul por defecto de Office, cada bloque con su etiqueta en mayúsculas, todo encajonado, mismo grid en las doce láminas.

Se rehízo con un sistema propio —fondo hueso, Georgia para títulos, acento terracota, tablas estilo *booktabs* sin relleno— y se verificó lámina por lámina exportándolas a PNG desde PowerPoint, lo que permitió detectar solapamientos, viudas tipográficas y conectores mal rematados que no se ven revisando el código.

---

## 4. Verificación

El criterio de reproducibilidad pesa 20 %, así que se verificó de forma explícita y no por inspección:

1. Se borraron `data/gold`, la base DuckDB y las salidas.
2. Se ejecutó `python run_all.py` en limpio.
3. Resultado: **exit 0 en 10 min 17 s**, con cifras idénticas a la corrida anterior.

La etapa de descarga tardó segundos en vez de minutos porque verificó los `sha256` del manifiesto y no volvió a bajar nada: eso es lo que demuestra la idempotencia. El grueso del tiempo —9 min 12 s— es la transformación, que lee los 5,4 GB de CSV; los cinco scripts restantes suman 15 segundos. Desde cero, con la descarga incluida, la corrida completa toma unos 18 minutos.

**Validación contra la fuente:** el total de ingresantes de pregrado 2025 que produce el modelo (495 089) coincide exactamente con el conteo directo sobre el CSV crudo, hecho con pandas antes de construir nada.

---

## 5. Revisión final

Terminado el pipeline, se hizo una pasada de revisión sobre el proyecto completo. Encontró **un bug de modelado y trece inconsistencias**, todas corregidas.

**El bug.** La medida `HHI Mediana Macrosur` filtraba por `dim_ubicacion[es_macrosur]`, pero `fct_concentracion` está a grano año × universidad y no se relaciona con esa dimensión. El filtro no propagaba y la medida devolvía la mediana nacional. DAX no emite ningún error en ese caso: simplemente no filtra. Se resolvió añadiendo `es_macrosur_sede` a `dim_universidad` y distinguiendo explícitamente las dos nociones de "sur" (ver D8 en el registro de decisiones).

**Lo demás:** conteos desactualizados entre documentos (relaciones, decisiones, clasificación de tendencias), constantes declaradas en `config.py` pero escritas a mano en el SQL y el DAX, `dim_tendencia_programa` sin cubrir los 53 programas sin matrícula —lo que dejaba huecos en la relación 1:1—, cifras de tiempo de ejecución que mezclaban escenarios con y sin descarga, y un par de detalles de estilo en el código.

Dos comprobaciones automatizadas que vale la pena conservar: validar que **todas las medidas DAX referencien columnas que existen** en el modelo real, y que **todos los enlaces entre documentos resuelvan**. Ambas pasaron tras las correcciones.

---

## 5b. Segunda revisión: sale Fabric, entra PySpark

Después de la primera revisión se decidió **no implementar la solución en Microsoft Fabric**. Es un cambio de alcance, no un recorte de calidad, y conviene dejar registrado cómo se propagó, porque toca el punto deseable 3.6.

**Qué obligó a replantear.** Hasta ese momento el proyecto decía, en siete sitios distintos, que la implementación en Fabric estaba *pendiente de activar el trial*. Eso convierte un requisito en una tarea sin terminar. Pero el enunciado nunca pidió implementarlo: ofrece **implementar o describir**. La corrección fue dejar de tratar la descripción como un plan B y asumirla como la opción elegida, con su sustento (decisión G3).

**El riesgo de describir y nada más.** Un diagrama de medallion lo dibuja cualquiera, y el argumento central del proyecto —"la lógica es portable porque vive en archivos `.sql`"— quedaba sin forma de comprobarse. Al ir a verificarlo apareció el hallazgo más incómodo de toda la revisión: **la afirmación era falsa**. `sql/portabilidad.md` decía que silver y gold corrían "sin cambios" en otro motor, pero gold usaba `arg_max()` doce veces, silver definía dos `CREATE MACRO`, y ninguna de las dos construcciones existe en PostgreSQL, T-SQL ni Spark.

**Cómo se resolvió, en este orden:**

1. **Medir antes de afirmar.** Se contaron las líneas que realmente requieren traducción: 25 de 255. La afirmación vaga pasó a ser una cifra.
2. **Bajar la cifra donde fuera gratis.** `arg_max()` → `max_by()` y `CAST(... AS VARCHAR)` → `VARCHAR(4)`: las dos formas las aceptan DuckDB y Spark por igual. Para Spark, las líneas a traducir pasaron de 25 a **4**, y `sql/gold/` quedó en **cero**.
3. **Verificar que el cambio no movía nada.** Se reconstruyó gold y se comparó la firma hash de las nueve tablas contra la versión anterior: idénticas.
4. **Escribir el código que lo demuestra.** `fabric/nb_01_transformar.py`: el notebook PySpark que ejecuta los mismos `.sql` sobre un Lakehouse, con `norm()` y `limpio()` como UDF.
5. **Verificar las UDF contra las macros.** Sobre los 1 299 valores distintos reales de departamento, provincia, programa, entidad y nivel: cero diferencias.
6. **Declarar lo no verificado.** El notebook no se ha ejecutado, porque no hay capacidad de Fabric. Está escrito en su propio encabezado y en `fabric/README.md`. El resto del proyecto solo reporta cifras medidas y esta parte no debía presentarse con la misma certeza.

**La lección.** Una afirmación cómoda que nadie ha intentado comprobar es deuda técnica disfrazada de documentación. Se sostuvo sin revisión hasta que un cambio de alcance obligó a apoyarse en ella.

**Otros defectos de esta pasada:** `campo_estudio` existía en `dim_programa` y en el diccionario pero faltaba en los dos DDL portables; el control del sesgo semestral estaba referenciado como `#7` en el código cuando es el `#08`; y las cifras de volumen mezclaban el plan descartado de 23 archivos (~7 GB) con el alcance real de 16 (5,4 GB, pico de 601 MB).

---

## 5c. Tercera revisión: se ingesta el catálogo completo

El pedido fue aumentar el volumen y tomar todas las fuentes disponibles, con una condición explícita: los datos descargados tienen que **transformarse y servir** para responder las preguntas, y puede haber datos que a pesar de bajarse aporten poco o nada. Había que resolver eso de forma razonable, no bajándolo todo y metiéndolo todo.

El orden del trabajo fue éste, y el orden importa: **primero medir, después decidir.**

**1. Inventariar el catálogo real.** Se consultó la API y se resolvió el tamaño de los 56 archivos sin descargarlos: nueve categorías, 1 270 MB. El proyecto tenía 16 archivos (588 MB). Saber que el total era 1,2 GB y no 7 GB cambió la conversación: duplicar la descarga era barato.

**2. Perfilar el esquema de cada categoría nueva antes de escribir un cargador.** Se bajó una muestra de egresados, docentes, carnés, GYT nacionales y GYT extranjeros, y se imprimieron sus columnas y una fila de ejemplo. De ahí salieron cuatro hallazgos que decidieron el diseño:

| Hallazgo | Consecuencia |
|---|---|
| Egresados trae `CODIGO_INEI` y `CODIGO_SIU_PROGRAMA` | Integra limpio: es un hecho más |
| Docentes **no** trae programa, y su geografía es el departamento de nacimiento | Hecho a grano universidad, declarado |
| GYT Nacionales trae `CODIGO_ENTIDAD` (`'065'`), no el código INEI | Llave por nombre normalizado, con tasa medida |
| GYT Extranjeros no contiene ninguna universidad peruana, y viene en UTF-16 | Fuera del modelo |

Escribir los cargadores antes de perfilar habría producido cuatro hechos, dos de ellos inútiles.

**3. Medir los campos antes de fijar el grano.** Dos mediciones cambiaron el modelo:

- `DEPARTAMENTO_FILIAL` en egresados está **vacío en el 100 %** de las 587 527 filas. El hecho se declara sin relación con `dim_ubicacion` en vez de imputar la sede de la universidad, que para las multi-filial habría sido inventar geografía.
- `PERIODO_EGRESO` trae periodos **3 y 4** (0,43 %) y 0,78 % vacíos. `dim_semestre` pasó de dos filas a tres, con una fila `'Otro'`, para que esas 7 126 filas no quedaran huérfanas al relacionar.

Las dos se descubrieron porque se midió el campo antes de escribir el `CREATE TABLE`, no después de que algo fallara.

**4. Convertir el recorte semestral en una dimensión.** Antes se descargaba solo el semestre I y el hecho se anclaba ahí. Con los 12 semestres cargados, el semestre pasó a ser parte del grano declarado y la serie anual comparable pasó a ser un **filtro de medida**. Lo que era una pérdida irreversible es ahora una decisión que el lector puede deshacer.

Eso introdujo el riesgo más serio de toda la revisión: `SUM(fct_matricula[matriculados])` ahora cuenta dos veces a quien estuvo matriculado todo el año. Se cubrió en tres sitios —la medida `Matriculados` con `CALCULATE`, el SQL de `04_tendencias.py`, y la instrucción de ocultar la columna base en la guía de armado— porque es un error que no rompe nada y falsea todo.

**5. Fijar el criterio de triaje, y hacerlo verificable.** Tres pruebas por dataset (llave, medida nueva, pregunta que responde), el resultado declarado en `referencias/datasets.csv`, y un control de calidad —el #13— que confronta esa declaración con el contenido real de la base en cada corrida. Sin el control, el CSV sería un comentario.

**6. Un fallo real que encontró el pipeline.** `GYT_Nacionales_2021.csv` abortaba la carga en la línea 45 400: la columna `PROGRAMA_ACREDITADO_SINEACE` traía el valor `"SI" RP.NRO.000135-2020-SINEACE/CDAH-P`, que empieza por comilla. Son **2 filas de 327 475** y impedían leer el archivo entero.

Se arregló con `quote=''` en los **siete** cargadores, no solo en el que falló: los planos de TUNI no entrecomillan nada, así que declararlo describe el formato real. Los otros seis funcionaban por casualidad. Es también la prueba de que el `ignore_errors=false` del resto del pipeline sirve para algo: con la configuración permisiva esas dos filas se habrían perdido en silencio.

**7. Propagar a todo lo demás.** Cuatro tablas nuevas obligaron a tocar, en orden: el DDL de silver, cuatro cargadores de bronze, siete archivos de gold, los dos DDL portables, el generador del diccionario, 14 medidas DAX nuevas más tres corregidas, seis controles de calidad nuevos más tres reescritos, la medición de portabilidad (397 líneas, no 255) y el notebook de Fabric.

Lo que hizo manejable esa propagación fue que la lógica vive en archivos `.sql` separados por capa y que las medidas salen de una sola lista en `05_powerbi.py`: no hubo que buscar nada en dos sitios. La decisión G4 —una sola fuente de verdad para las medidas— se pagó aquí.

**8. Lo que las fuentes nuevas aportaron de verdad.** El criterio no era «más datos»: era si el dato responde algo que antes no se podía responder.

| Fuente | Lo que habilita |
|---|---|
| Docentes | Ratio alumno/docente y % a tiempo completo: **Condiciones Básicas de Calidad del licenciamiento SUNEDU**. El benchmark de la 4.1 pasa de ser de tamaño a ser de capacidad. |
| Egresados | Cierre del embudo y la única medida de desempeño académico del portal (nota promedio) |
| GYT Nacionales | Tasa de titulación: titularse no es lo mismo que egresar |
| Los 12 semestres | Retención intra-anual, imposible con un solo semestre por año |

Tres fuentes no aportaron: carnés universitarios (cuenta trámites, no alumnos), oferta universitaria (sus atributos ya vienen repetidos en las tablas de personas) y GYT extranjeros (no tiene universidad peruana). Las tres se descargan, se perfilan y se declaran. **Esa declaración es parte del entregable, no un residuo.**

**9. Tres cosas más que encontró la verificación, no la lectura del código.** Las tres aparecieron después de que el modelo estuviera construido, al cronometrar o al ampliar una comprobación. Vale separarlas porque ninguna se habría visto revisando el código a ojo.

*El `GUID` de carnés no identifica personas.* Se descubrió porque el control #12 daba un ratio de 0,10 %, imposible con 2,86 millones de filas de carnés contra 1,5 millones de matriculados. `COUNT(DISTINCT guid_persona)` devolvía 321 valores para 405 488 filas. Al mirarlos, cada GUID corresponde a **una** universidad pero a decenas de programas, con conteos redondos (12 000, 20 000): es un identificador de **lote de emisión**. El control #12 pasó a contar filas y se añadió el **#15** para publicar la anomalía. El hallazgo **confirma** la decisión de no usar carnés como hecho: una fuente que no permite contar personas no puede medir matrícula. Si se hubiera usado, la medida habría dado un número plausible y falso.

*Las macros de normalización dejaban pasar el espacio duro.* La verificación de las UDF del notebook de Fabric contra las macros de DuckDB daba **cero diferencias sobre 1 299 valores**. Al ampliarla a los **8 763** valores de texto de silver aparecieron **cuatro**: `trim()` de DuckDB no quita tabuladores y su `\s` no cubre `chr(160)`, mientras los de Python sí. Las macros eran las que estaban mal —`silver_titulo.nombre_entidad` trae 588 filas con un espacio duro dentro del nombre, o sea dentro de una llave de texto—. Se corrigieron las dos y las UDF se reescribieron para replicarlas; `norm()` quedó incluso más corta, porque ahora reutiliza `limpio()`.

*La idempotencia era cierta y a la vez inútil.* La etapa de descarga tardaba **154 s** en una reejecución donde no había nada que bajar, porque resolvía cada archivo en SharePoint —tres llamadas HTTP, 168 en total— *antes* de comparar el hash. Y esa resolución no aportaba nada: la comparación es contra el hash del manifiesto, no contra el del servidor. Indexando el manifiesto por `(categoría, periodo)` en vez de por nombre de archivo, la etapa baja a **2 s** y a cero llamadas. El límite que esto introduce —no detectar un periodo republicado— ya existía antes, y ahora está declarado y es operable con `--revalidar`.

**10. Lo que cambió en el método, a raíz de lo anterior.** Dos comprobaciones pasaron a ser parte del proyecto en vez de scripts de usar y tirar:

| Script | Qué responde | Coste |
|---|---|---|
| `validar_sql.py` | ¿Se puede ejecutar todo el SQL? Crea silver vacío y corre gold más calidad | 3 s |
| `fabric/verificar_udf.py` | ¿Las UDF del notebook producen lo mismo que las macros? | ~30 s |

El primero existe porque la carga real tarda 19 minutos y un error de sintaxis en `sql/gold/` no se descubriría hasta el final. El segundo extrae las funciones **del propio notebook** en vez de llevar una copia: una copia en el test podría quedar desincronizada del código que se entrega, que es exactamente el error que el test existe para evitar.

**11. La lección transversal de esta revisión.** Las cuatro correcciones de peso —la comilla embebida, el GUID de lote, el espacio duro y la resolución innecesaria— tienen la misma forma: **algo que se daba por bueno sin medirlo**. Dos de ellas (el filtro de pregrado, la idempotencia) eran afirmaciones correctas que no significaban lo que parecían. Las otras dos eran defectos que ninguna lectura del código habría encontrado, porque no eran errores de lógica sino supuestos sobre los datos y sobre el coste.

## 5d. Cuarta revisión: evaluación crítica contra la rúbrica

Antes de entregar, la solución se evaluó como lo haría un revisor con poco tiempo, criterio por criterio. Encontró defectos que ninguna de las revisiones anteriores había visto, porque solo aparecen al **consultar el modelo cargado** y no al leer el código:

| Defecto | Cómo se detectó | Corrección |
|---|---|---|
| La regresión solo cubría matrícula; la 4.3 pide también ingresantes | Lectura del enunciado | Regresión sobre las dos series y lectura cruzada (decisiones E1, E6) |
| "Estable" contra "Volátil" decidido con el R²: 135 programas que crecían más de 10 % al año salían estables | Distribución de las clases | Cuatro clases, sin R² (E3) |
| Arquitectura salía "+30 % anual" con un ingreso que cae | Comparar ingreso y matrícula de la UCSP | El ingreso manda en la lectura (E6) |
| La matrícula se sumaba entre años: 52 864 en vez de 9 188 | Consulta DAX sin filtro de año | Stocks semi-aditivos (F9) |
| La guarda de grano no cubría la macrorregión | Consulta DAX con el sur filtrado | Guarda sobre la tabla (F12) |
| Comparadores que ignoraban la gestión: la selectividad se invertía | Tasa de admisión por gestión | `ALLEXCEPT` y comparador de privadas (F10) |
| Ratio del país mezclaba universidades sin docentes: 20,9 en vez de 19,5 | Consulta DAX contra SQL | Universo común (F11) |
| La tabla de tendencia mostraba promedios nacionales con la UCSP seleccionada | Consulta DAX por programa | `SELECTEDVALUE` y filtro `es_ucsp` (F13) |
| La lámina del modelo describía el modelo anterior | Lectura de la PPT | PPT reestructurada por requerimiento 3.1 a 3.6 |

El modelo se cargó en Power BI Desktop por código, con el servidor MCP de Microsoft. Cada corrección se verificó con una consulta DAX contra la cifra que da el pipeline en SQL. Las 25 relaciones se probaron en tres frentes: llaves únicas, cero filas huérfanas y una matriz de propagación filtro por filtro.

El tablero pasó de cinco páginas a tres, para una lectura gerencial (F14). El README se redujo a ejecución, pipeline y duración.

---

## 6. Qué se haría distinto

Registrado con franqueza, porque es lo que suele preguntarse en una sustentación:

- **Perfilar las cuatro fuentes antes de diseñar el modelo, no tres.** El esquema de postulantes se revisó cuando ya estaban escritas las tablas de silver, y resultó tener `ES_INGRESANTE`, una columna que habría cambiado antes el diseño de la pregunta 4.4.
- **Empezar por un control de nulos sobre la capa silver.** El problema de la clasificación CINE se detectó en la fase de calidad, cuando ya existían las dimensiones. Mirarlo en silver lo habría anticipado.
- **Versionar con Git desde el primer commit.** Se trabajó sobre carpeta plana por decisión de alcance; con control de versiones, revertir la primera versión de `dim_programa` habría sido inmediato en vez de manual.
- **Fijar el sistema visual de la presentación antes de escribirla.** Rehacer la maquetación costó más que haberla definido al principio.

---

## 7. Cómo retomar este proyecto

Para alguien que lo reciba sin contexto:

1. **Leer el [`README.md`](../README.md)** — qué hace, cómo se ejecuta, qué quedó fuera.
2. **Ejecutar `python run_all.py`** — unos 18 minutos desde cero, y se reconstruye todo.
3. **Leer [`decisiones_tecnicas.md`](decisiones_tecnicas.md)** antes de cambiar cualquier regla del modelo. Varias decisiones que parecen arbitrarias tienen evidencia detrás; la sección final lista los ocho hallazgos de los datos que condicionaron el diseño.
4. **Para cambiar el alcance temporal o las fuentes:** editar `ANIOS` y `ARCHIVOS` en `config.py`. No hay nada más que tocar.
5. **Para cambiar la macrorregión sur:** editar `referencias/macrorregiones.csv` y reejecutar con `--solo-gold`.
6. **Para añadir una fuente nueva** (egresados, docentes): crear `sql/bronze/<fuente>.sql` siguiendo el patrón de los tres existentes, añadir la tabla silver en `sql/silver/00_tablas.sql`, y un `sql/gold/2x_fct_<fuente>.sql`. El resto del modelo no se toca, porque las dimensiones ya están conformadas.
7. **Para migrar de motor:** ver [`sql/portabilidad.md`](../sql/portabilidad.md). Solo cambia `sql/bronze/`.

---

## 8. Uso de inteligencia artificial generativa en el proceso

Se usó **Claude (Anthropic)** como asistente de desarrollo, de forma intensiva y en concreto para:

| Fase | Aporte |
|---|---|
| Exploración | Ingeniería inversa del front-end de tuni.pe hasta reproducir la cadena de descarga; diagnóstico del `403` de SharePoint y del encoding cp1252 |
| Planificación | Borrador del plan y su corrección tras la revisión del volumen |
| Código | Redacción de los siete scripts y del SQL, con ejecución y verificación de cada etapa |
| Documentación | Borradores del README, el diccionario, el catálogo de medidas, la PPT y este documento |

Lo que **no** delegó: el recorte temporal y su justificación estadística, la granularidad de los hechos, el criterio de homologación, la definición de "tendencia sostenida", los umbrales, y la decisión de qué dejar fuera. Esas decisiones se tomaron explícitamente y están registradas con su sustento en [`decisiones_tecnicas.md`](decisiones_tecnicas.md).

Todas las cifras citadas en la documentación y en la presentación provienen de ejecutar el pipeline, no del modelo de lenguaje: el diccionario se genera leyendo la base construida, y la presentación también, con un script que no forma parte de la entrega.
