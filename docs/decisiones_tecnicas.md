# Registro de decisiones técnicas

Cada decisión no trivial tomada durante la construcción, con su sustento, las alternativas descartadas y la evidencia que la respalda. Pensado como material de consulta para la sustentación técnica.

Formato: **Contexto → Decisión → Por qué → Alternativa descartada → Evidencia**.

---

## A. Ingesta

### A1. Descargar por la API de TUNI en vez de descarga manual

**Contexto.** `tuni.pe/datos` es una SPA de Angular; el botón "Descargar" no expone una URL de archivo. El requisito 3.1 exige que el proceso corra de principio a fin sin pasos manuales.

**Decisión.** Ingeniería inversa del front-end para descubrir la API y automatizar la cadena completa de 5 pasos:

1. `POST /api/serviciotuni/listar` → catálogo (categoría, periodo, id).
2. `POST /api/serviciotuni {"archivos":[id]}` → `webUrl` de SharePoint.
3. `GET <webUrl>?download=1` → fija la cookie `FedAuth` anónima y devuelve el HTML con `rootFolder`.
4. `GET /_api/web/GetFolderByServerRelativeUrl(...)/Files` → nombre y tamaño del zip interno.
5. `GET /_api/web/GetFileByServerRelativeUrl(...)/$value` → descarga.

**Por qué.** Es la única forma de cumplir "sin pasos manuales" literalmente. Además hace que agregar un periodo nuevo sea cambiar una lista en `config.py`, no volver a navegar el portal.

**Alternativa descartada.** Descarga manual documentada en el README. Cumple a medias y no permite la actualización programada en Fabric.

**Evidencia / hallazgos no obvios.**
- **El paso 4 es obligatorio.** Sin consultar el listado de la carpeta, el paso 5 devuelve `403`. Los 5 pasos deben correr en la misma `requests.Session()`.
- **El header `Origin: https://tuni.pe` debe mandarse solo a la API de TUNI, nunca a SharePoint**: SharePoint lo rechaza con `403`. Esto costó varias iteraciones de diagnóstico y es la causa de que un script ingenuo falle.
- La ruta del zip es `/DocumentosTUNI/<hash>_<dataset>.csv.zip/<otro_hash>_<dataset>.csv.zip` — una carpeta que *se llama* `.zip` y contiene el zip real.

### A2. Manifiesto con sha256, y la idempotencia que de verdad ahorra

**Contexto.** `data/bronze/manifiesto.csv` registra categoría, periodo, id, nombre, bytes y **sha256** de cada archivo descargado.

**Por qué el hash y no el tamaño.** Una descarga interrumpida puede dejar un archivo del tamaño correcto con contenido corrupto. El hash lo detecta; el tamaño no. Y ese mismo `sha256` sirve para tres cosas sin escribir nada más: evitar redescargar 1 270 MB, dejar trazabilidad de qué archivo exacto produjo cada resultado, y detectar un periodo nuevo en la propuesta de Fabric.

**La corrección que hizo falta medir para encontrar.** La primera versión funcionaba así: resolver el archivo en SharePoint (pasos 2, 3 y 4 de la cadena) y *después* comparar el hash local contra el del manifiesto para decidir si descargar. Medido, la etapa tardaba **154 s** en una reejecución donde no había nada que bajar.

El motivo: resolver un archivo cuesta **tres llamadas HTTP**, o sea 168 para el catálogo completo, y eso era el 68 % del tiempo de la etapa. Peor aún, esa resolución **no aportaba nada**: el paso 5 compara el hash local contra el del manifiesto, no contra el del servidor, así que la ruta resuelta se descartaba.

**Decisión.** El manifiesto se indexa por `(categoría, periodo)` —la clave del catálogo— y si el zip local sigue coincidiendo con su hash, se salta también la resolución.

| | Antes | Ahora |
|---|---|---|
| Reejecución de la etapa 01 | 154 s | **2 s** |
| Llamadas HTTP cuando nada cambió | 168 | **0** |

**Lo que esto NO detecta, y hay que decirlo.** Si SUNEDU republica un periodo con el contenido corregido, el zip local sigue intacto y el atajo lo da por bueno. **La versión anterior tampoco lo detectaba**, por el motivo de arriba — la diferencia es que ahora la limitación está declarada y es operable: `python 01_descargar.py --revalidar` fuerza la resolución completa contra la fuente (medido: 160 s, resuelve los 56 y no descarga ninguno porque los hashes coinciden).

**La lección.** Una propiedad que se afirma sin medir puede ser cierta y a la vez inútil. La idempotencia estaba bien implementada y ahorraba 71 s de 1 393; el cuello estaba en otra parte, y solo apareció al cronometrar la etapa.

## B. Alcance y volumen

### B1. Ingestar el catálogo completo: 56 archivos, 1 270 MB

**Contexto.** El portal publica **nueve categorías** de datos y **56 archivos CSV** en total. Una versión anterior de este proyecto ingestaba 16 (588 MB), recortando años y semestres para ahorrar descarga y tiempo de proceso.

**Decisión.** Ingestar **todo el catálogo, sin recorte**: los 56 archivos, 1 270 MB de zips, con su `sha256` en el manifiesto.

**Por qué.** Porque la ingesta **está automatizada**, y eso cambia el cálculo. Un recorte de ingesta se justifica cuando bajar datos cuesta trabajo humano; cuando cuesta una llamada más en un bucle, el recorte solo traslada el costo al futuro: la primera pregunta que necesite el semestre II o el año 2020 obliga a volver a la fuente, y volver a la fuente es la parte frágil de todo el pipeline (SharePoint puede cambiar, un periodo puede republicarse).

Bajarlo todo una vez cuesta 1,2 GB de disco y unos 11 minutos. No bajarlo cuesta una re-ingesta cada vez que cambia una pregunta.

**El principio que esto establece, y que gobierna el resto del diseño:**

> **La ingesta no decide nada. El modelo decide todo.**

Bronze es la foto de lo que SUNEDU publicó, completa y verificable por hash. Las decisiones analíticas —qué periodo, qué grano, qué fuente— se toman más adelante, donde son reversibles sin tocar la red.

**Lo que esto NO significa.** No significa que los nueve datasets entren al modelo. Significa que la razón por la que uno no entra queda **medida y escrita** en vez de disuelta en un recorte de descarga. Ver B5.

### B2. El semestre deja de ser un recorte y pasa a ser una dimensión

**Contexto.** La matrícula se publica por semestre (12 archivos, 2020-I a 2025-II); ingresantes y postulantes son anuales. Antes el proyecto descargaba **solo el semestre I** de cada año y anclaba el hecho ahí, con 2025-II bajado aparte únicamente para medir el sesgo de ese recorte.

**Decisión.** Cargar los 12 semestres. `fct_matricula` pasa a tener el **semestre como parte del grano declarado**, y la serie anual comparable se obtiene filtrando `dim_semestre[es_serie_anual]`.

**Por qué importa la distinción.** Es el mismo número con un estatus distinto:

| | Antes | Ahora |
|---|---|---|
| El semestre II | no estaba descargado | está en el modelo |
| La serie anual | un **recorte de datos** | un **filtro de medida** |
| Si alguien lo pregunta | hay que re-ingestar | se quita el filtro |
| El control #08 | estimaba un sesgo con 1 año | mide retención en 6 años |

Un recorte de datos es irreversible sin volver a la fuente. Un filtro de medida es una decisión que el lector puede deshacer.

**Lo que habilita, y antes era imposible:** la **retención intra-anual** (matrícula del semestre II sobre la del I del mismo año), que es un indicador real del sector y que con un solo semestre por año no tenía con qué compararse.

**El riesgo que introduce, y cómo se cubre.** Con los 12 semestres cargados, un `SUM(fct_matricula[matriculados])` cuenta **dos veces** a quien estuvo matriculado todo el año. Es un error que no rompe nada y falsea todo. Se cubre en tres sitios: la medida `Matriculados` fija el semestre con `CALCULATE`; `04_tendencias.py` lo filtra en el SQL de la serie; y la guía de armado manda ocultar la columna base para que nadie pueda arrastrar una agregación implícita al lienzo.

### B2b. 2020 se ingesta, pero no entra en la regresión

**Contexto.** Con el catálogo completo hay seis años de matrícula (2020–2025) en vez de cinco. Para OLS simple eso sería mejor: `gl = n − 2` pasa de 3 a 4, y el `t` crítico al 95 % baja de 3,182 a 2,776.

**Decisión.** La ventana de la regresión sigue siendo **2021–2025**. 2020 está cargado, es visible en el dashboard y se puede filtrar, pero `dim_periodo[es_tendencia]` lo deja fuera del test.

**Por qué se renuncia a un grado de libertad.** Porque 2020 fue el año de ruptura por la pandemia, con congelamientos masivos de matrícula. Incluirlo convierte el **rebote** posterior en pendiente: el modelo reportaría como "crecimiento sostenido" lo que es una recuperación del nivel previo. La pregunta 4.3 pide tendencia estructural, no recuperación.

**La diferencia con la versión anterior de esta decisión.** Antes el argumento era el mismo pero no se podía comprobar, porque 2020 no estaba descargado. Ahora el **control de calidad #14** publica la variación interanual de cada par de años consecutivos, así que el lector ve el salto de 2020 a 2021 al lado de los demás y juzga por sí mismo. La decisión pasó de afirmación a evidencia.

**Dónde vive.** `config.py → ANIOS_TENDENCIA`, propagado a `ref_parametros` y de ahí a `dim_periodo[es_tendencia]`. No hay un literal `2021` escondido en ningún `.sql`.

### B3. Procesar un archivo a la vez

**Contexto.** Los 56 CSV del catálogo, descomprimidos, suman del orden de **11 GB** (matriculado 2025-I solo pesa 601 MB). El plan inicial, con los 12 semestres de matrícula, llegaba a ~7 GB.

**Decisión.** Bucle descomprimir → agregar en DuckDB → borrar el CSV.

**Por qué.** El pico de disco pasa a ser el archivo más grande (601 MB) en vez de la suma. Importa en un portátil y, sobre todo, evita que OneDrive intente sincronizar gigabytes.

**Evidencia.** Huella final: 1 270 MB de zips + unos 4 MB de parquets gold. Las tablas de hechos tienen entre 10 mil y 16 mil filas: **todo el detalle persona a persona se consume en la agregación y no sobrevive al modelo**.

### B4. Filtrar a pregrado: `NIVEL_ACADEMICO = 'Carrera Profesional'`

**Por qué.** El enunciado pide explícitamente "programa profesional de pregrado". El resto de la fuente es Maestría, Doctorado y Segunda Especialidad.

**Evidencia.** Control #1: retiene 79–83 % de los ingresantes y 91–93 % de los matriculados, consistente año a año. Se reporta como filtro declarado, no como pérdida.

---

### B5. Qué entra al modelo: tres pruebas medibles

**Contexto.** Si la ingesta baja los nueve datasets, hace falta un criterio para decidir cuáles llegan a ser hechos. Sin criterio explícito, "bajamos todo" degenera en "metimos todo", que es peor que un recorte: infla el modelo con tablas que nadie puede cruzar.

**Decisión.** Cada dataset pasa tres pruebas, y las tres respuestas son **números o hechos verificables**, no opiniones:

1. **¿Tiene llave?** ¿Se une a `codigo_inei` y/o `codigo_siu_programa` sin inventar correspondencias?
2. **¿Aporta una medida que no exista ya?** ¿Mide algo que ninguna otra fuente mide mejor?
3. **¿Sirve a una pregunta del §4 o a un requisito del §3?**

Las tres → **hecho en gold**. Falla la 2 → **uso de contraste o referencia**. Falla la 1 → **se queda en bronze, con el motivo escrito**.

**Resultado aplicado:**

| Dataset | Llave | Medida nueva | Pregunta | Destino |
|---|---|---|---|---|
| Matriculado | sí | — (es la central) | 4.1 4.2 4.3 | hecho |
| Ingresante | sí | sí | 4.1 4.2 | hecho |
| Postulante | sí | sí | 4.4 | hecho |
| Egresado | sí | nota, créditos | 4.1 4.4 | hecho |
| Docente | solo universidad | ratio alumno/docente | 4.1 | hecho a grano universidad |
| GYT Nacionales | por nombre normalizado | titulación efectiva | 4.4 | hecho, con tasa de match publicada |
| **Carnés Universitarios** | sí | **no** — peor proxy de lo que ya mide la matrícula | 3.2 | **contraste de calidad** |
| **Oferta universitaria** | sí | **no** — gestión, licenciamiento y sede ya vienen en las tablas de personas | — | **referencia** |
| **GYT Extranjeros** | **no** — son universidades extranjeras | fuera de dominio | — | **solo bronze** |

**Por qué el triaje está en un CSV y no en prosa.** Vive en `referencias/datasets.csv`, y el **control de calidad #13** confronta esa declaración con el contenido real de la base: si alguien escribe un cargador y olvida declararlo, o declara `gold` para un dataset que no llegó, el control sale en `REVISAR`. Una declaración que nadie verifica es un comentario; una que se verifica en cada corrida es parte del pipeline.

**Los dos casos que más vale la pena defender en la sustentación:**

*Carnés universitarios* pasa la prueba de llave perfectamente y aun así no es un hecho. Cuenta **trámites administrativos**, no alumnos: un estudiante de cinco años puede tener un carné o ninguno. Como medida de matrícula es estrictamente peor que la matrícula. Pero precisamente por venir de un proceso distinto sirve de **contraste independiente** (control #12): si divergiera mucho de la matrícula, el hallazgo sería sobre la fuente.

*GYT Nacionales* **falla** la prueba de llave en su forma estricta —no trae `CODIGO_INEI`, solo `CODIGO_ENTIDAD`, que es otro código— y entra de todos modos, por excepción declarada: se resuelve con un join de **igualdad sobre el nombre normalizado**, que no es fuzzy matching, y el control #11 publica qué porcentaje resuelve. Se acepta porque es la única fuente que mide **titulación efectiva** frente a egreso. Lo que no se acepta es bajar al grano de programa: `NOMBRE_CARRERA` es texto libre, y resolverlo exigiría fuzzy matching sobre 2 438 nombres. Ahí se traza la línea.

## C. Formato y lectura de los datos

### C1. El encoding es cp1252, no latin-1

**Contexto.** DuckDB rechazó la lectura con `encoding='latin-1'`: *"File is not latin-1 encoded"*.

**Decisión.** Instalar la extensión `encodings` de DuckDB y leer con `encoding='cp1252'`.

**Por qué.** El diagnóstico fue contar bytes por rango: aparecen **71 ocurrencias del byte `0x96`** (guion largo en cp1252), que ISO-8859-1 deja indefinido. Es decir, los archivos son Windows-1252, no latin-1 — una diferencia que solo se manifiesta en un puñado de filas y que habría corrompido texto de forma silenciosa si se hubiera forzado la lectura.

**Para la portabilidad.** En Spark es `.option("encoding","windows-1252")`, en PostgreSQL `ENCODING 'WIN1252'`, en SQL Server `CODEPAGE='1252'`.

### C2. Delimitador pipe y nulos como `<NULL>`

**Decisión.** Dos macros SQL reutilizables: `limpio(s)` convierte `'<NULL>'` y cadena vacía en `NULL` real; `norm(s)` además quita tildes, pasa a mayúsculas y colapsa espacios, para usar como llave.

**Por qué.** Concentra la normalización en un solo lugar en vez de repetir `nullif(nullif(...))` en cada columna de cada cargador.

### C3. `institucional.csv` tiene las columnas desalineadas

**Hallazgo.** Ese archivo (a diferencia del resto) es separado por coma **y** usa coma como separador decimal en latitud/longitud: las filas traen 29 campos contra 27 del encabezado.

**Decisión.** No se incorpora al modelo. Se descarga y se documenta el defecto.

**Por qué.** Sus dos aportes posibles (duración del programa, modalidad) no responden a ninguna de las cuatro preguntas, y su llave de programa (`PROGRAMA_CODIGO`) no es la misma que `CODIGO_SIU_PROGRAMA` de los datasets transaccionales, así que el join no sería fiable.

---

### C4. `quote=''`: los planos de TUNI no entrecomillan, y uno lo demuestra

**Contexto.** `GYT_Nacionales_2021.csv` abortaba la carga en la línea 45 400. La columna `PROGRAMA_ACREDITADO_SINEACE` traía el valor `"SI" RP.NRO.000135-2020-SINEACE/CDAH-P`.

**El mecanismo del fallo.** El campo **empieza** por comilla. DuckDB autodetecta `"` como carácter de cita, lo toma como apertura de un campo entrecomillado, no encuentra el cierre que la gramática CSV exige, y aborta el archivo entero. Son **2 filas de 327 475** las que tienen la comilla: 0,0006 % del archivo impide leer el 100 %.

**Decisión.** Declarar `quote=''` en los **siete** cargadores de `sql/bronze/`, no solo en el que falló.

**Por qué en todos y no solo en el que rompía.** Porque el formato real de la fuente es *pipe-delimited sin entrecomillado*: el separador es el `|` y las comillas que aparecen son literales. `quote=''` no es un parche para un archivo, es la descripción correcta del formato. Los otros seis cargadores funcionaban por casualidad —ningún campo suyo empieza por comilla hoy—, y ese es exactamente el tipo de dependencia que rompe cuando SUNEDU publique el siguiente periodo.

**Alternativas descartadas.**

| Opción | Por qué no |
|---|---|
| `ignore_errors=true` | Descartaría silenciosamente las filas malas. Un pipeline que pierde datos sin decirlo es peor que uno que falla. |
| `strict_mode=false` | Relaja la gramática en general en vez de declarar el formato concreto. Tolera el síntoma sin nombrar la causa. |
| Preprocesar el CSV quitando comillas | Añade un paso de reescritura de 174 MB y una copia del archivo. El lector ya sabe hacerlo bien si se le dice la verdad sobre el formato. |

**Qué prueba este hallazgo.** Que el `ignore_errors=false` del resto del pipeline sirve para algo. Con la configuración permisiva, estas dos filas se habrían perdido sin dejar rastro y nadie habría mirado nunca la columna.

## D. Modelo de datos

### D1. La llave de programa es compuesta: `(codigo_inei, codigo_siu_programa)`

**Contexto.** Lo natural sería usar `CODIGO_SIU_PROGRAMA` como llave del programa.

**Decisión.** Llave compuesta, materializada como `programa_sk = md5(codigo_inei || '-' || codigo_siu_programa)`.

**Por qué.** **`CODIGO_SIU_PROGRAMA` no es único a nivel nacional.**

**Evidencia.** En ingresantes 2025, **288 de 471 códigos distintos aparecen en más de una universidad**. Usarlo solo como llave habría fusionado programas de universidades diferentes bajo un mismo registro — un error silencioso que no produce ningún mensaje y corrompe todas las comparaciones. Es probablemente el hallazgo con mayor impacto de todo el ejercicio.

### D2. Dos dimensiones de tiempo, cada una en su grano → estrella pura

**Contexto.** Seis hechos con dos granos temporales distintos: matrícula, egresados y docentes son **semestrales** en la fuente; ingresantes, postulantes y títulos son **anuales**.

**Decisión.** Dos dimensiones conformadas, no una:

- `dim_periodo` a grano **año**, relacionada con **los seis** hechos. Es el grano común a todos.
- `dim_semestre` a grano **periodo lectivo**, relacionada **solo con los tres** semestrales.

**Por qué no una sola `dim_periodo` semestral de 24 filas.** Porque obligaría a colgar los hechos anuales de la fila `-I` de cada año, y eso **afirma algo falso**: que un ingresante ingresó en el semestre I. Un modelo no debe inventar precisión que la fuente no tiene.

**Por qué no el semestre como columna suelta en cada hecho** (dimensión degenerada). Porque son tres hechos los que lo tienen, no uno. Con una dimensión conformada el informe lleva **un solo segmentador** que filtra los tres a la vez; con una columna por hecho harían falta tres segmentadores sincronizados a mano, y el primero que alguien olvide sincronizar produce una página incoherente.

**El resultado sigue siendo estrella pura**, sin snowflake: `dim_semestre` cuelga directamente de los hechos, no de otra dimensión.

**El detalle que casi se escapa.** `dim_semestre` tiene **tres** filas, no dos. Medido sobre los cuatro archivos de egresados, `PERIODO_EGRESO` no trae solo `1` y `2`: trae también `3` y `4` (2 553 filas, 0,43 %) y 4 573 filas sin periodo (0,78 %). Son egresos extraordinarios. Con solo dos filas, esas 7 126 filas quedarían **huérfanas** al relacionar y desaparecerían del informe sin aviso. La fila `0 = 'Otro'` las recoge: el 100 % de los egresados queda representado y la rareza se vuelve visible. El control #05 lo verifica en cada corrida.

### D3. Ubicación a grano departamento + provincia, no local

**Contexto.** Los filtros obligatorios incluyen departamento y macrorregión.

**Decisión.** `dim_ubicacion` con llave `md5(departamento || '-' || provincia)` normalizados.

**Por qué.** Es la **intersección real** entre las fuentes: ingresantes y postulantes traen `CODIGO_SIU_FILIAL` / `DEPARTAMENTO_FILIAL`, matriculados trae `CODIGO_LOCAL` / `DEPARTAMENTO_LOCAL`. Los códigos de sede **no son el mismo identificador**, así que un grano a nivel local no sería conciliable entre hechos. Departamento y provincia sí lo son.

**Siguiente paso declarado.** Si se necesitara el detalle por local, habría que construir una tabla puente de equivalencias entre `CODIGO_SIU_FILIAL` y `CODIGO_LOCAL`, que la fuente no provee.

### D4. Atributos divergentes: último valor **no nulo**, no última fila

**Contexto.** El nombre de una universidad o la clasificación CINE de un programa pueden variar entre periodos, o estar presentes un año y ausentes al siguiente.

**Decisión.** Para cada atributo por separado, `max_by(atributo, anio) FILTER (WHERE atributo IS NOT NULL)`.

**Por qué.** La primera versión tomaba la fila completa del año más reciente (`ROW_NUMBER() ... ORDER BY anio DESC`). Eso descarta la clasificación CINE de un programa cuyo último año la trae vacía, aunque exista en años previos.

**Evidencia.** El cambio redujo los programas sin campo CINE de **415 a 225** de 2 733 — recuperó 190 programas (46 % de los que faltaban) sin inventar ningún dato: solo usando lo que la propia fuente ya había declarado antes.

**Sobre portabilidad.** Se escribe `max_by` y no el alias `arg_max` de DuckDB porque Spark acepta el primero y no el segundo (ver G5). En PostgreSQL se traduce a `(array_agg(x ORDER BY anio DESC) FILTER (WHERE x IS NOT NULL))[1]` y en T-SQL a una subconsulta `ROW_NUMBER()`. Documentado en `sql/portabilidad.md`.

### D5. Homologación de programas por CINE-UNESCO, sin fuzzy matching

**Contexto.** La pregunta 4.3 exige comparar "programas equivalentes" entre universidades. Hay 2 438 nombres de programa distintos.

**Decisión.** Usar `NOMBRE_GRUPO_3` (83 campos detallados) y `NOMBRE_GRUPO_1` (11 campos amplios) de la clasificación **CINE-UNESCO que la propia fuente de SUNEDU ya trae**.

**Por qué.** Es el criterio oficial del regulador, es auditable, y hace el código trivial (un `GROUP BY`) en vez de requerir una librería de similitud de cadenas con umbrales arbitrarios que habría que justificar uno por uno.

**Alternativa descartada.** Fuzzy matching sobre `nombre_programa` con `rapidfuzz`/`difflib`. Más código, más frágil, y cualquier umbral elegido sería discutible en la sustentación.

**Limitación honesta.** ~20 % de las filas crudas no traen clasificación CINE, y quedan 225 programas sin campo tras D4 (13,6 % de la matrícula nacional). Se etiquetan explícitamente como `Sin clasificar CINE` para que sean visibles en el dashboard en vez de desaparecer como BLANK.

**Dato relevante.** Los **13 programas de pregrado de la UCSP tienen clasificación CINE completa**, así que la pregunta 4.3 se responde sin huecos para el caso de interés.

### D6. Macrorregión sur: 8 departamentos, en un CSV editable

**Decisión.** Sur = **Arequipa, Cusco, Puno, Moquegua, Tacna, Apurímac, Ayacucho, Madre de Dios**, definido en `referencias/macrorregiones.csv`.

**Por qué.** Sur andino más selva sur, según el agrupamiento usado por INEI/CEPLAN. **Ica queda fuera** porque suele asociarse a la macrorregión centro-sur.

**Por qué en un CSV y no en el código.** Es un criterio discutible; dejarlo como dato de referencia lo hace auditable y reversible sin tocar SQL. Si el evaluador prefiere otra agrupación, es editar una línea y reejecutar.

### D7. Siete tablas de hechos, no una tabla consolidada

**Decisión.** `fct_ingresantes`, `fct_matricula`, `fct_postulantes`, `fct_egresados`, `fct_docentes` y `fct_titulos`, cada una con su granularidad declarada arriba del `CREATE TABLE`.

**Por qué no una sola tabla con una columna `tipo_hecho`.** Porque los granos no coinciden. Matrícula es año × semestre × universidad × programa × ubicación; docentes es año × semestre × universidad. Una tabla consolidada obligaría a rellenar con nulos las columnas que un tipo de hecho no tiene, y un `NULL` en una columna de grano no es un dato ausente: es una fila que significa otra cosa. Las medidas tendrían que filtrar por `tipo_hecho` en todas partes.

**Tres hechos no se relacionan con todas las dimensiones, y es por medición, no por olvido:**

| Hecho | Grano | No se relaciona con | Motivo medido |
|---|---|---|---|
| `fct_egresados` | año × semestre × univ × programa | `dim_ubicacion` | `DEPARTAMENTO_FILIAL` y `PROVINCIA_FILIAL` vienen **vacíos en el 100 %** de las 587 527 filas. La fuente publica un código de local que no coincide con el de ningún otro dataset del portal. |
| `fct_docentes` | año × semestre × univ | `dim_programa`, `dim_ubicacion` | La fuente no trae `CODIGO_SIU_PROGRAMA`. Su única geografía es el departamento de **nacimiento** del docente, que no es donde enseña. |
| `fct_titulos` | año × univ | `dim_programa`, `dim_ubicacion` | Trae `NOMBRE_CARRERA` en texto libre, no el código. Resolverlo exigiría fuzzy matching sobre 2 438 nombres. |

**La alternativa descartada, y es la tentadora.** Para egresados se podría imputar el departamento de la sede principal de su universidad. Para una universidad de un solo local sería correcto. Para las que tienen filiales en varios departamentos sería **inventar geografía**, y el dato inventado se ve exactamente igual que el real en un visual. Se prefiere una relación que falta y está declarada a un dato que parece existir.

**Dónde se paga el precio de esa honestidad.** El segmentador de departamento —filtro obligatorio del enunciado— no filtra egresados, docentes ni títulos. Eso podría producir lecturas falsas al cruzar medidas de distinto grano, y por eso existe la decisión F7.

### D8. Dos nociones distintas de "sur": dónde se imparte vs. de dónde es la universidad

**Contexto.** `fct_docentes` no trae programa ni ubicación, así que **no se relaciona con `dim_ubicacion`**. Una medida "del sur" sobre docentes que filtrara por `dim_ubicacion[es_macrosur]` no propagaría: devolvería el valor nacional etiquetado como "del sur", sin dar error.

**Decisión.** Añadir a `dim_universidad` los atributos `departamento_sede`, `macrorregion_sede` y `es_macrosur_sede`, donde la sede principal es el departamento en el que la universidad concentra más matrícula. `Ratio Alumno Docente Macrosur` filtra por `dim_universidad[es_macrosur_sede]`.

**Por qué el modelo necesita las dos nociones.** No son intercambiables:

| Atributo | Qué marca | Para qué sirve |
|---|---|---|
| `dim_ubicacion[es_macrosur]` | **dónde se imparte** un programa | El filtro obligatorio del enunciado; `Matrícula Macrosur` |
| `dim_universidad[es_macrosur_sede]` | **de dónde es** la universidad | Comparar instituciones entre sí, como el ratio alumno/docente |

Una universidad de Lima con filial en Cusco aporta matrícula a la macrorregión sur, pero no es una universidad del sur. Para "¿cuánta matrícula hay en el sur?" cuenta la primera; para "¿cuántos alumnos por docente tienen las universidades del sur?" cuenta la segunda.

**Alternativa descartada.** Asignar a cada docente una ubicación a partir de las filiales de su universidad. La fuente no trae ese vínculo: repartirlos entre filiales sería inventar el dato.

**Evidencia.** 39 universidades quedan con sede principal en la macrorregión sur, 81 en el centro, 34 en el norte y 6 en el oriente; 3 quedan sin clasificar por no registrar matrícula en ningún periodo I del recorte. La UCSP se resuelve correctamente como Arequipa.

**Lección metodológica.** Un filtro DAX sobre una dimensión que no está relacionada con la tabla de hechos **no produce ningún error**: simplemente no filtra. Es un fallo silencioso, del mismo tipo que el de la llave de programa (D1), y solo se detecta revisando el modelo contra las medidas.

---

### D9. Los parámetros de modelado viven en una tabla, no en literales repetidos

**Contexto.** Dos valores gobiernan el modelo desde fuera: cuál es el semestre de la serie anual comparable, y qué años entran en la regresión. Los necesitan `config.py`, varios `.sql` de gold, `04_tendencias.py` y las medidas DAX.

**Decisión.** `config.py` los declara una vez; `sql/silver/01_referencias.sql` los materializa en una tabla `ref_parametros` de una fila; gold los lee de ahí (`dim_semestre[es_serie_anual]`, `dim_periodo[es_tendencia]`), y las medidas DAX filtran por esos **atributos con nombre** en vez de por un número.

**Por qué no simplemente escribir `semestre = 1` donde haga falta.** Porque habría **dos verdades**: un `1` en `config.py` y varios `1` repartidos en `.sql`, sin nada que los mantenga sincronizados. El día que alguien cambie el de `config.py`, el SQL seguirá con el viejo y el pipeline no fallará — producirá números distintos de los documentados. Es la peor clase de error: silencioso y plausible.

El costo de evitarlo son cuatro líneas de SQL. El beneficio adicional es que el dashboard filtra por `dim_semestre[es_serie_anual]`, que se lee solo, en vez de por un literal que hay que ir a buscar.

## E. Componente estadístico

### E1. OLS sobre `log(y)`, en dos series: ingresantes y matrícula

**Decisión.** Regresión lineal simple de `log(y)` contra el año, 2021–2025, por programa, sobre ingresantes **y** sobre matrícula.

**Por qué en logaritmo.** La pendiente **es** la tasa de crecimiento anual compuesta (`CAGR = exp(pendiente) − 1`). Eso hace comparables programas de tamaños muy distintos: una carrera que pasa de 80 a 120 alumnos y otra de 800 a 1 200 tienen la misma pendiente. En niveles, la segunda dominaría siempre.

**Por qué dos series.** La pregunta 4.3 pide tendencia "en ingresantes y matrícula", y la primera versión solo regresaba la matrícula. Ver E6.

**Alternativa descartada.** CAGR punta a punta, que es la medida `CAGR Matricula` del modelo. Se conserva para el rango que elige el usuario, pero ignora los tres años intermedios. Sustento completo, con las demás alternativas del enunciado, en `docs/componente_estadistico.md`.

### E2. p-valor con `scipy.stats.t`, no con tabla de valores críticos

**Decisión.** `p = 2 * stats.t.sf(abs(t), df=n-2)`.

**Por qué.** scipy ya estaba instalado en el entorno. Una línea y el p-valor es exacto, en vez de aproximarlo con una tabla de valores críticos codificada a mano.

### E3. "Tendencia sostenida" = tres condiciones simultáneas, y cuatro clases

**Decisión.** Una serie tiene tendencia sostenida si cumple ≥ 4 años con dato **y** `p < 0,05` **y** `|CAGR| ≥ 3 %`. Clases: crecimiento sostenido, caída sostenida, sin tendencia sostenida y serie insuficiente.

**Por qué.** Cada condición descarta un falso positivo distinto:
- la primera, series demasiado cortas;
- la segunda, pendientes que no se distinguen del ruido;
- la tercera, pendientes significativas pero irrelevantes en magnitud.

**Corrección en la revisión.** La primera versión separaba "Estable" de "Volátil" con el R². El R² mide qué parte de la variación explica la pendiente, y en una serie plana es ~0 por construcción. El efecto, medido: **135 programas que crecían o caían más de 10 % al año salían como "Estable"**, y las series más quietas salían como "Volátil".

Además, el 57 % de los ingresos con pendiente plana oscila más de un 10 % alrededor de ella, así que llamarlos estables sobreafirma. La distinción se eliminó.

**Resultado** sobre los 2 812 programas:

| Clase | Ingresantes | Matrícula |
|---|---|---|
| Crecimiento sostenido | 198 | 589 |
| Caída sostenida | 133 | 416 |
| Sin tendencia sostenida | 1 500 | 1 215 |
| Serie insuficiente | 981 | 592 |

> La tabla cubre **todos** los programas de `dim_programa`. Los que no tienen serie entran como `Serie insuficiente`, así la relación 1:1 con `dim_programa` queda completa.

### E4. El benchmark sectorial excluye a la UCSP

**Decisión.** El CAGR del campo CINE en la macrorregión sur se calcula **excluyendo `codigo_inei = '260000062'`**.

**Por qué.** Si no, la UCSP se compararía contra una serie que la incluye. En campos donde la UCSP es un actor grande, eso amortiguaría la diferencia justo donde más importa detectarla.

**Para qué sirve.** Separa dos diagnósticos que de otro modo se confunden: *el programa cae porque el campo entero cae en el sur* (problema de mercado) frente a *el programa cae mientras el campo crece* (pérdida de competitividad).

**Evidencia del valor de esta decisión.** En Ingeniería Industrial de la UCSP, la matrícula cae **−7,0 %** al año (p = 0,007) mientras la del mismo campo en el sur crece **+4,4 %**. En ingresantes, el programa está en +0,6 % y su campo en +10,3 %. Sin el comparador, el dato aislado se podría atribuir a una caída general del sector; con él, queda claro que no.

### E5. La distribución de la matrícula se muestra, no se resume en un índice

**Decisión.** La pregunta 4.1 pide la distribución de la matrícula por programa. Se responde con las barras de matrícula por programa y su participación en la universidad, sin un índice de concentración.

**Por qué.** Un índice como el de Herfindahl-Hirschman resume la distribución en un número que hay que explicar antes de poder leerlo. Las barras la muestran directamente: qué programas pesan más y cuánto.

**Alternativa descartada.** El HHI por universidad y año, comparado con la mediana del sur. Se construyó y se retiró: sumaba una tabla, dos relaciones y tres medidas sin cambiar la lectura de la pregunta.

### E6. La lectura cruza las dos series, y manda el ingreso

**Decisión.** Cada programa recibe una lectura que combina las dos tendencias. Por ejemplo, *crecimiento confirmado* exige crecer en las dos; *alerta: cae el ingreso* es el ingreso en caída con la matrícula todavía sin caer.

**Por qué.** La matrícula es un stock que acumula cohortes: un programa abierto en 2020 llena sus cinco años de alumnos aunque su ingreso caiga. Medido en la UCSP:

| Programa | Matrícula | Ingresantes |
|---|---|---|
| Arquitectura y Urbanismo | +29,8 % al año (p = 0,002) | **−4,1 %** (p = 0,012) |
| Ingeniería Mecatrónica | +28,0 % | +2,5 %, no significativo |
| Ingeniería Ambiental | +23,4 % | −12,6 %, no significativo |

Con una sola serie, los tres eran "crecimiento sostenido". El ingreso es el indicador adelantado; la matrícula lo confirma con rezago.

**Resultado UCSP.** Ningún programa con crecimiento confirmado. Contabilidad y Administración tienen caída confirmada. Arquitectura queda en alerta.

---

## F. Capa semántica y DAX

### F1. `ALLSELECTED` en los rankings, no `ALL`

**Decisión.** `RANKX ( ALLSELECTED ( dim_programa[nombre_programa] ), ... )`.

**Por qué.** Es la diferencia entre un ranking que responde a los filtros y uno que los ignora. Con `ALL`, el ranking se calcula sobre el universo completo y no cambia al mover los slicers de universidad, departamento, gestión o periodo — lo contrario de lo que exige explícitamente la pregunta 4.2.

### F2. Umbral mínimo en el bottom-5

**Decisión.** `Ranking Programa Inverso` excluye programas con menos de 10 matriculados.

**Por qué.** Sin umbral, el fondo del ranking lo ocupan siempre programas que abrieron ese año con 2 o 3 alumnos, y el visual deja de informar sobre demanda baja para informar sobre programas nuevos. El umbral se declara en la PPT y es un parámetro en `config.py`.

### F3. Series indexadas a base 100 para el benchmark

**Decisión.** Tres medidas `Índice Matrícula UCSP / Macrosur / Nacional`, con base en el primer año seleccionado.

**Por qué.** La UCSP tiene ~9 mil matriculados y el total nacional ~1,55 millones. En valores absolutos, graficar las tres series juntas produce una línea plana y una que ocupa todo el eje. Indexadas, las tres son comparables y la pregunta 4.1 se responde de un vistazo.

### F4. Sin funciones de time intelligence

**Decisión.** El desplazamiento interanual es explícito: `CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )`.

**Por qué.** `dim_periodo[anio]` es un entero, no una fecha. Marcar una tabla de 5 filas como tabla de fechas para poder usar `SAMEPERIODLASTYEAR` sería introducir un artefacto (365 × 5 filas de calendario) que ninguna medida del modelo necesita.

### F5. Selectividad desde `ES_INGRESANTE`, sin cruzar fuentes

**Contexto.** La idea inicial era calcular la selectividad cruzando `fct_postulantes` con `fct_ingresantes`.

**Decisión.** Usar la columna `ES_INGRESANTE` que trae el propio dataset de postulantes: `Tasa de Admisión = DIVIDE([Admitidos], [Postulaciones])`.

**Por qué.** Numerador y denominador salen del mismo archivo y del mismo proceso de admisión, así que el ratio no depende de que dos datasets independientes sean consistentes entre sí.

**Beneficio inesperado.** Como las dos fuentes son independientes, comparar ambas se convierte en un **control de calidad cruzado**: el control #9 verifica que los admitidos que declara el dataset de postulantes coincidan con los ingresantes del dataset de ingresantes. Desvío de **+2,98 % (2022), +0,57 % (2023), +0,23 % (2025)**. Dos sistemas de reporte distintos de SUNEDU concuerdan dentro del 3 %, lo que da confianza en ambos.

### F6. Qué filtros quita cada medida de comparación, declarado explícitamente

**Contexto.** Las medidas que comparan contra un agregado mayor —participación, benchmark, cuota— tienen que quitar algún filtro para construir su denominador. Elegir mal cuál se quita no produce ningún error: produce otro número. Es la clase de defecto más difícil de ver en DAX.

**Decisión.** Dos reglas, aplicadas de forma uniforme:

**1. Participación: el denominador reimpone la universidad del programa.** `% Participación en su Universidad` no se queda en `REMOVEFILTERS(dim_programa)`. Captura la universidad del programa en contexto y la vuelve a aplicar con `TREATAS` sobre `dim_universidad`:

```dax
VAR SuUniversidad = VALUES ( dim_programa[codigo_inei] )
VAR MatriculaUniversidad =
    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_programa ),
                TREATAS ( SuUniversidad, dim_universidad[codigo_inei] ) )
```

Sin el `TREATAS`, en una tabla que no esté filtrada a una universidad el denominador es el **total nacional**, no el de su universidad — que es justo lo que pide el 3.4. Hace falta `TREATAS` y no una relación porque `dim_programa[codigo_inei]` es atributo descriptivo, no llave foránea (ver D1).

**2. Las tres series de referencia definen su cohorte igual.** `Matrícula UCSP`, `Matrícula Macrosur` y `Matrícula Nacional` quitan **las mismas dos** dimensiones —universidad y ubicación, las que definen cada cohorte— y respetan **las mismas dos** —periodo y programa, las que hacen comparables las series. Al filtrar un campo de estudio, las tres muestran ese campo.

**Por qué importa la simetría.** El gráfico indexado de la pregunta 4.1 superpone las tres. Si una respeta el filtro de campo y otra no, el gráfico compara cosas distintas y nadie lo nota: las tres líneas siguen dibujándose.

**La contrapartida, declarada.** Al quitar `dim_universidad` también se pierde el filtro de gestión en esas tres medidas. Es deliberado —una cohorte de referencia que cambia con los segmentadores deja de ser referencia— y está anotado en la guía de armado para que el gráfico se titule en consecuencia. El resto de los visuales de la página sí responden a los cuatro filtros obligatorios.

**Cómo se encontró.** En la segunda revisión, releyendo las medidas contra el enunciado en vez de contra sí mismas. Es el mismo tipo de fallo que describe D8: DAX no avisa cuando un filtro no propaga.

---

### F7. Guardas de grano: una medida que no puede responder, devuelve BLANK

**Contexto.** `fct_docentes` y `fct_titulos` están a grano universidad: no se relacionan con `dim_programa` ni con `dim_ubicacion` (ver D7). Pero el informe sí lleva segmentadores de programa y de departamento, porque los otros hechos los necesitan.

**El error que esto provoca, si no se cubre.** Con un programa filtrado, `Ratio Alumno Docente = DIVIDE([Matriculados], [Docentes])` tiene un numerador que **sí** cae al programa filtrado y un denominador que **sigue siendo todo el plantel de la universidad**. El resultado serían 3 alumnos por docente: un número plausible, formateado, y completamente falso.

Es la misma clase de error que los dos bugs DAX corregidos en F6 — una medida que mezcla contextos de filtro asimétricos y no avisa.

**Decisión.** `Ratio Alumno Docente` y `Titulados por Egresado` llevan una guarda explícita:

```dax
VAR FiltroFino =
    ISFILTERED ( dim_programa[nombre_programa] )
    || ISFILTERED ( dim_programa[campo_estudio] )
    || ISFILTERED ( dim_ubicacion[departamento] )
    || ISFILTERED ( dim_ubicacion[provincia] )
RETURN
    IF ( FiltroFino, BLANK (), DIVIDE ( [Matriculados], [Docentes] ) )
```

**Por qué BLANK y no el número de la universidad.** Devolver el ratio de la universidad entera mientras el visual dice "Ingeniería Industrial" sería atribuir a un programa un dato que no es suyo. Devolver `BLANK()` dice la verdad: a este grano la pregunta no tiene respuesta en la fuente.

**El costo es de experiencia de usuario, y se paga en el diseño del informe.** Una tarjeta vacía se lee como error. Por eso el prototipo pone un cuadro de texto al lado, y el catálogo de medidas lo declara en la descripción de cada una — que es lo que Power BI muestra al pasar el cursor.

**La alternativa descartada** era no crear estas medidas. Pero el ratio alumno/docente es una Condición Básica de Calidad del licenciamiento SUNEDU: es exactamente el indicador con el que la reguladora mide a las universidades. Renunciar a él para evitar una tarjeta vacía sería renunciar a lo más relevante que aportó la fuente nueva.

### F8. El nombre de una medida es parte de su corrección

**Contexto.** La primera versión de la capa semántica tenía una medida `Tasa de Titulacion = DIVIDE(SUM(fct_titulos[titulos]), [Egresados])`. Al rellenar las cifras del prototipo con datos reales, devolvió **206 %** para la UCSP en 2024.

**Qué estaba mal, en orden de descubrimiento.** Tres cosas distintas, y las tres se midieron:

**1. El numerador contaba eventos, no personas.** `fct_titulos[titulos]` es un `COUNT(*)` sobre grados y títulos conferidos. Medido: **437 872 personas tienen dos** —el grado de bachiller *y* el título profesional— y 4 153 tienen tres o más. Se añadió `personas` al hecho (`COUNT(DISTINCT guid_persona)`), que es la única cifra comparable con un conteo de egresados.

**2. Numerador y denominador describen cohortes distintas.** Los títulos se confieren años después del egreso. Medido en la UCSP para 2024: **876 grados de bachiller contra 755 egresados del año**. Más bachilleres que egresados, porque los grados corresponden a quienes egresaron antes. La división es legítima; llamarla *tasa* no lo es.

**3. Las dos fuentes no cubren el mismo universo.** El control de calidad **#17** cuenta entre **17 y 43 universidades** que reportan matrícula y no reportan egresados, según el año. Y el **#16** mide `egresado 2025-II` al **55 %** del volumen típico de su fuente: SUNEDU publica un periodo en cuanto lo tiene, no cuando está cerrado.

**Decisión.** Tres cambios, uno por cada defecto:

| Qué | Cómo queda |
|---|---|
| `fct_titulos` | Guarda `titulos` (eventos) **y** `personas` (distintas). Las dos cifras existen porque responden preguntas distintas |
| La medida | Se llama **`Titulados por Egresado`**, usa `[Personas Tituladas]`, y su descripción declara el rezago de cohorte y el problema de cobertura |
| El dashboard | La tarjeta de la página 4 muestra **`Personas Tituladas`**, un volumen. El cociente vive en la tabla de detalle |

**Por qué el nombre importa tanto como la fórmula.** `Tasa de Titulacion` promete que el numerador es un subconjunto del denominador: *de los que egresan, cuántos se titulan*. La fórmula no podía cumplirlo, y con ese nombre el 206 % se lee como un error de cálculo en vez de como lo que era —una división entre dos cosas que no se corresponden—. `Titulados por Egresado` describe exactamente la operación que hace y no promete nada más.

**Por qué la tarjeta pasó a ser un volumen.** Una tarjeta KPI es el peor sitio para un número con dos confusiones: el formato —cifra grande, una línea de título— promete una conclusión que el dato no soporta. En una tabla, al lado de sus componentes y con la columna de año visible, el mismo número es informativo.

**Alternativa descartada.** Borrar la medida. Se descartó porque la relación entre titulación y egreso es un indicador real de eficiencia institucional, y filtrada a **una** universidad que reporte las dos fuentes el cociente sí es interpretable. Lo que había que arreglar era la promesa, no el cálculo.

**La lección, que es la misma de B2b y A2.** Las cifras del prototipo se rellenaron desde la base precisamente para que un número imposible saliera a la luz. Si se hubieran escrito a mano valores plausibles, la medida habría llegado al dashboard con su nombre equivocado.

### F9. Los stocks son semi-aditivos en el año

**Decisión.** `Matriculados`, `Docentes` y `Programas Activos` devuelven el **último año** del contexto, no la suma ni el promedio del rango.

**Por qué.** La misma persona está matriculada cada año que estudia. Medido: sin la regla, una tarjeta sin filtro de año daba **52 864** matriculados para la UCSP; el valor es 9 188.

Los flujos (ingresantes, egresados, postulaciones) sí se suman. Para las fichas existe `Ingresantes Ultimo Anio`.

### F10. Los comparadores respetan la gestión

**Decisión.** Las series del sur y del país usan `ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] )` en vez de `REMOVEFILTERS ( dim_universidad )`. En selectividad, el comparador por defecto son las **privadas del sur**.

**Por qué.** En 2025 la UCSP admite el 56 % de sus postulaciones. El resto del sur, el 34 %; las privadas del sur, el 77 %; las públicas, el 14 %. Contra el sur completo, la UCSP parece menos selectiva; contra sus pares privados lo es más. Un comparador que ignora la gestión **invierte la conclusión**, y la gestión es además un filtro obligatorio.

### F11. Los cocientes entre fuentes usan el universo común

**Decisión.** `Ratio Alumno Docente`, `Egresados por Ingresante` y `Titulados por Egresado` suman numerador y denominador solo sobre las universidades que reportan las dos fuentes, y en un mismo año.

**Por qué.** El cociente directo del país daba 20,9 alumnos por docente; sobre el universo común, 19,5. La diferencia son universidades con matrícula y sin docentes reportados. Es el mismo error que producía el 206 % de titulación (F8).

### F12. Guardas sobre la tabla, no sobre columnas sueltas

**Decisión.** `ISFILTERED ( dim_programa ) || ISFILTERED ( dim_ubicacion )`.

**Por qué.** La guarda anterior enumeraba cuatro columnas y dejaba fuera la macrorregión, que es un filtro obligatorio. Con el sur seleccionado, el ratio alumno/docente dividía la matrícula del sur entre el plantel de todo el país.

### F13. Medidas de tendencia con `SELECTEDVALUE`, y filtro de visual por programa

**Decisión.** Las medidas que leen `dim_tendencia_programa` son `SELECTEDVALUE`, no `AVERAGE`. Los visuales de la 4.3 se filtran con `dim_programa[es_ucsp]`.

**Por qué.** El segmentador de universidad no llega a `dim_programa`, porque las dimensiones no se relacionan entre sí. Con `AVERAGE`, la fila "Derecho" mostraba el promedio de los cien programas de Derecho del país aunque estuviera seleccionada la UCSP. Con `SELECTEDVALUE` el error es visible (un blanco) en lugar de silencioso.

### F14. Tres páginas ejecutivas, con titulares que se reescriben

**Decisión.** El tablero pasa de cinco páginas a tres:
- **Posición de mercado**, para la 4.1;
- **Portafolio de programas**, para la 4.2 y la 4.3;
- **Admisión y selectividad**, para la 4.4.

Cada página abre con un titular calculado en DAX (`Titular Resumen`, `Titular Tendencia`, `Titular Selectividad`).

**Por qué.** El público es la dirección universitaria. Una frase que responde y cambia con los filtros no puede contradecir a los visuales de abajo. La calidad de datos sale del tablero: su evidencia está en el CSV, la PPT y `docs/controles_calidad.md`.

---

## G. Arquitectura e ingeniería

### G1. DuckDB como motor de desarrollo, con la lógica fuera de Python

**Decisión.** DuckDB para el desarrollo local; **toda la lógica en archivos `.sql`** segmentados en `bronze/` (atado al motor), `silver/` y `gold/` (portables; las salvedades, medidas por motor, en `sql/portabilidad.md`). Python solo orquesta.

**Por qué.** DuckDB procesa los ~590 MB sin servidor y con una sola dependencia, y el enunciado valora especialmente el uso de SQL. Pero la UCSP usa SQL Server o Postgres, así que el diseño debe sobrevivir al cambio de motor: por eso la separación por capas.

**El argumento de fondo.** En producción la institución **no ingiere CSVs de SharePoint**: ingiere de su SIS/ERP, que ya está en una base relacional. La única capa atada a DuckDB — `sql/bronze/`, la lectura de archivos planos — **es exactamente la capa que desaparece** en el entorno real.

**Lo que sí habría que reescribir** (detallado con equivalencias en `sql/portabilidad.md`): `read_csv` → `BULK INSERT`/`COPY`; `md5()` → `HASHBYTES`; `strip_accents()` → `unaccent()`/colación acento-insensible; `max_by` → subconsulta con `ROW_NUMBER()` en T-SQL; `UNPIVOT` del control #4 → `UNION ALL` en Postgres. CTEs, funciones de ventana, `COUNT(DISTINCT)`, `CASE` y joins son idénticos en los cuatro motores.

**Nota sobre Fabric.** El SQL Analytics Endpoint y el Warehouse de Fabric son T-SQL, así que la columna de SQL Server de esa tabla no es un ejercicio teórico: es lo que se ejecuta al migrar al Warehouse. Si en cambio se usa el Lakehouse con notebooks, aplica Spark, y ahí la traducción es de 4 líneas (ver G5).

### G2. Controles de calidad como un único SQL

**Decisión.** Los 17 controles viven en `sql/calidad.sql` como un solo resultset (`control | detalle | valor | umbral | estado`). `03_calidad.py` solo lo ejecuta y lo exporta.

**Por qué.** Los mismos controles se pueden pegar tal cual en el SQL Endpoint de Fabric o en SSMS, sin Python de por medio. Y el resultado es una tabla, no texto en consola, así que sirve directamente como anexo de evidencias.

### G3. Responder el 3.6 describiendo la arquitectura, no montando el workspace

**Contexto.** El requerimiento 3.6 (deseable) admite dos caminos: *implementar* la solución en Microsoft Fabric **o** *describir* sus capas, orquestación y actualización programada. Hay que elegir uno.

**Decisión.** Describir el diseño, y entregar el `.pbix` como entregable 5.1 único. Sin enlace a workspace.

**Por qué.** Tres razones, en orden de peso:

1. **Lo verificable es lo que se puede ejecutar.** El criterio de mayor peso (3.1, 20 %) es la reproducibilidad. El evaluador puede comprobarla corriendo `python run_all.py`. Un workspace de Fabric no se puede ejecutar desde fuera: solo mirarse, y solo con acceso al tenant.
2. **Una capacidad de prueba caduca y puede no abrirse desde otro tenant.** Un enlace que deja de funcionar a mitad del proceso de selección es peor entregable que un `.pbix` que abre siempre.
3. **La pregunta es de arquitectura, y la arquitectura ya está tomada.** Lo que determina si esto corre en Fabric se decide al escribir el código —lógica en `.sql` por capa, manifiesto sha256, hechos pequeños—, no al crear el workspace.

**Alternativa descartada.** Montar el trial y entregar el enlace además del `.pbix`. Se descartó al ver que el tiempo de montaje compraba un entregable frágil, mientras que el mismo tiempo invertido en escribir el notebook PySpark (ver G5) deja evidencia permanente y revisable.

**Cómo se mitiga el riesgo de "describir y nada más".** Un diagrama de medallion lo dibuja cualquiera. Por eso la respuesta al 3.6 no es solo `docs/arquitectura_fabric.md`: incluye `fabric/nb_01_transformar.py`, el notebook PySpark que ejecuta los mismos `.sql` sobre Spark. Está declarado como no ejecutado, pero es código revisable.

### G4. Las medidas viven en el modelo y el catálogo las documenta

**Decisión.** Las 76 medidas están en el modelo entregado, `UCSP_Benchmark.pbix`. [`docs/catalogo_medidas.md`](catalogo_medidas.md) documenta cada una: qué mide, la fórmula DAX y el formato.

**Por qué.** El entregable pide el modelo (5.1) y el catálogo (5.3). Los scripts con que se cargaron las medidas serían copias adicionales de las mismas fórmulas: más archivos que revisar y más lugares donde pueden desincronizarse.

### G5. SQL escrito para que lo acepten DuckDB y Spark sin traducción

**Contexto.** La capa de transformación se desarrolla en DuckDB, pero el perfil del puesto pide PySpark y la arquitectura propuesta corre sobre un Lakehouse. Si el SQL usa funciones propias de DuckDB, la portabilidad deja de ser una afirmación verificable.

**Decisión.** Donde hay dos formas de escribir lo mismo, usar la que aceptan ambos motores:

| En vez de | Se escribió | Aceptan |
|---|---|---|
| `arg_max(x, y)` | `max_by(x, y)` | DuckDB y Spark |
| `CAST(anio AS VARCHAR)` | `CAST(anio AS VARCHAR(4))` | DuckDB, Spark, PostgreSQL y T-SQL |

**Por qué.** Coste cero en el momento de escribirlo, y el resultado es medible: **`sql/gold/` corre sobre Spark sin una sola modificación.** De las 255 líneas de `sql/silver/` y `sql/gold/`, solo **4** necesitan traducción a Spark, todas en silver: las dos macros y la lectura del CSV de referencia.

**Evidencia.** Al aplicar el cambio se reconstruyó la capa gold y se comparó la firma hash de las nueve tablas contra la versión anterior: **idénticas**. La sustitución es semánticamente neutra.

**Alternativa descartada.** Mantener `arg_max` y documentar la traducción. Es lo que había antes de esta revisión; convertía una afirmación demostrable en una promesa.

### G6. El modelo se verifica por consulta DAX contra el pipeline

**Decisión.** El modelo semántico se cargó en Power BI Desktop mediante el servidor MCP oficial de Microsoft. Cada cifra clave se consultó por DAX y se contrastó con el SQL del pipeline.

**Por qué.** La consulta encontró defectos que una revisión visual no habría visto (F9 a F13). La herramienta es parte de la revisión, no del pipeline: lo que se entrega es el `.pbix` ya verificado.

### G7. La generación de la presentación queda fuera del repositorio

**Decisión.** El script que genera la PPT vive fuera del repositorio. Se entrega la presentación, no cómo se produce.

**Por qué.** No es parte de la solución analítica que se evalúa, y quitarlo reduce lo que el revisor tiene que leer. Con él salió también la dependencia `python-pptx`.

---

## H. Qué quedó fuera, y por qué

### H0. Los tres datasets que se descargan y no llegan a ser hechos

Están en bronze con su `sha256`, perfilados, y declarados en `referencias/datasets.csv`. No llegan a gold por motivos distintos:

| Dataset | Por qué no |
|---|---|
| **GYT Extranjeros** (6 archivos, 6 MB) | Es el registro de **reconocimiento de títulos obtenidos en universidades extranjeras**. No contiene ninguna universidad peruana, así que no hay llave con la que unirlo al modelo: responde una pregunta distinta (convalidación de credenciales), no una sobre la oferta académica peruana. Además viene en **UTF-16**, no en cp1252 como el resto del portal — una incoherencia de la fuente que vale documentar. |
| **Carnés Universitarios** (5 archivos, 83 MB) | Cuenta trámites, no alumnos. Ver B5: se usa como contraste independiente de la matrícula en el control #12, no como hecho. |
| **Oferta universitaria** (1 archivo, 0,3 MB) | Catálogo institucional. Todo su contenido útil —gestión, licenciamiento, tipo de constitución, sede— ya viene repetido en cada fila de las tablas de personas, de donde `dim_universidad` lo toma con la regla del último valor no nulo. Cargarlo añadiría una segunda fuente para los mismos atributos y, con ella, la posibilidad de que discrepen. |


| Elemento | Motivo |
|---|---|
| Años 2020 de ingresantes y matriculados | Ruptura COVID; ver B1 |
| Periodo II de cada año (salvo 2025-II para validar) | Grano anual; sesgo medido en −2,81 %, ver B2 |
| Posgrado (maestría, doctorado, segunda especialidad) | El enunciado pide pregrado; ver B4 |
| Datasets de Egresados, Docentes, GYT y Carnés | Alcance acotado; el enunciado valora priorizar sobre cubrirlo todo |
| `institucional.csv` en el modelo | Columnas desalineadas y llave de programa no conciliable; ver C3 |
| Detalle por local/filial | Los códigos de sede no son conciliables entre fuentes; ver D3 |
| Dimensión de sexo, edad y discapacidad | Disponible en silver, fuera del modelo gold: ninguna de las cuatro preguntas la requiere. Añadirla sería ampliar `fct_*` sin uso |
| Fuzzy matching de nombres de programa | La fuente ya trae la clasificación oficial CINE; ver D5 |

---

## I. Hallazgos de los datos que condicionaron el diseño

Resumen de lo que no se sabía al empezar y cambió decisiones:

1. **`CODIGO_SIU_PROGRAMA` se repite entre universidades** (288 de 471). → Llave compuesta (D1).
2. **La fuente ya trae la clasificación CINE** en dos niveles. → Homologación sin fuzzy matching (D5).
3. **El dataset de postulantes trae `ES_INGRESANTE`.** → Selectividad sin cruzar fuentes, y control cruzado gratis (F5).
4. **El encoding es cp1252, no latin-1** (71 bytes `0x96`). → Extensión `encodings` de DuckDB (C1).
5. **El header `Origin` rompe las llamadas a SharePoint.** → Headers por host (A1).
6. **~20 % de las filas no traen CINE**, y el último año de un programa puede venir vacío. → `max_by ... FILTER`, que recuperó 190 programas (D4).
7. **La matrícula del periodo II es solo 2,81 % menor que la del I.** → Valida el recorte semestral (B2).
8. **Los códigos de local difieren entre ingresantes y matriculados.** → Ubicación a grano departamento+provincia (D3).
9. **Las series truncadas son cierres, no fallas de la fuente.** De las 35 universidades que no reportan matrícula en los cinco años, **23 tienen licencia denegada** por SUNEDU y solo 8 están licenciadas. → Justifica excluirlas del análisis de tendencia en vez de imputarles los años faltantes, y convirtió el control 07 de un conteo sin interpretación en un hallazgo del sector (abierto por licenciamiento con `ROLLUP`).
10. **Todo postulante de pregrado declara programa de primera opción.** El filtro del cargador descarta 0 filas en los cuatro años. → El control 02 puede exigir conciliación exacta en las tres fuentes, sin excepciones.
