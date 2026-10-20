# Arquitectura en Microsoft Fabric

Este documento responde al **requerimiento 3.6**, que pide *implementar o describir* la solución en Microsoft Fabric, con sus **capas de datos, la orquestación y la actualización programada**.

Se tomó la segunda opción: **describir el diseño**. No es un reemplazo de la implementación, es la otra alternativa que el enunciado ofrece, y se eligió por tres razones concretas.

**1. El criterio de mayor peso es la reproducibilidad, y solo se puede verificar en local.** El 3.1 vale 20 % y pide un proceso ejecutable de principio a fin sin pasos manuales. Un evaluador puede comprobarlo corriendo `python run_all.py` en su propia máquina. Un área de trabajo de Fabric no se puede ejecutar desde fuera: solo se puede mirar, y únicamente si se tiene acceso al tenant. Apoyar el entregable en algo que el evaluador no puede ejecutar reduce lo verificable, no lo aumenta.

**2. Un área de trabajo de prueba caduca y puede no abrirse desde otro tenant.** La capacidad de evaluación de Fabric tiene plazo, y el acceso de invitados externos depende de la configuración del tenant de origen. Un enlace que deja de funcionar a mitad del proceso de selección es peor entregable que un `.pbix` que abre siempre.

**3. La pregunta de 3.6 es de arquitectura, y la arquitectura ya está tomada.** Las decisiones que determinan si este proyecto corre en Fabric no se toman al montar el workspace: se toman al escribir el código. Están tomadas, y se pueden señalar en el repositorio:

| Decisión de diseño | Dónde está | Qué habilita en Fabric |
|---|---|---|
| Lógica en archivos `.sql` por capa, Python solo orquesta | `sql/silver/`, `sql/gold/` | Los notebooks se reducen a leer cada archivo y ejecutarlo |
| Manifiesto con sha256 por archivo | `data/bronze/manifiesto.csv` | Es el mecanismo de detección de periodo nuevo del Pipeline |
| Medallion bronze / silver / gold | `02_transformar.py` | Mapea 1:1 a `Files/` y `Tables/` del Lakehouse |
| Modelo estrella con hechos pequeños (10–16 mil filas) | `sql/gold/` | Es lo que hace apropiado Direct Lake |
| Medidas DAX en un script de Tabular Editor | `powerbi/medidas.csx` | Se aplica igual sobre un modelo Direct Lake |
| **El notebook PySpark ya escrito** | [`fabric/nb_01_transformar.py`](../fabric/nb_01_transformar.py) | Ejecuta los mismos `.sql` sobre Spark |

Y para que esto no se quede en un diagrama: el notebook PySpark que implementa la capa de transformación **está escrito y entregado** en [`fabric/`](../fabric/). No se ha ejecutado —no hay capacidad— y así se declara, pero es código revisable, no una promesa.

Lo que sigue es ese diseño, con el detalle que haría falta para montarlo.

---

## Plano local (el que corre hoy)

```
TUNI.PE API ──► 01_descargar.py ──► data/bronze/*.zip + manifiesto.csv (sha256)
                                          │
                          ┌───────────────┴────────────────┐
                          │  bucle por archivo (pico 601MB)│   BRONZE
                          │  unzip → DuckDB → borrar CSV   │
                          └───────────────┬────────────────┘
                                          │  02_transformar.py + sql/
                                   ┌──────┴──────┐
                                   │   DuckDB    │  SILVER (tipado + normalizado)
                                   └──────┬──────┘  GOLD   (estrella agregada)
                                          ▼
                                 data/gold/*.parquet  (~1 MB)
                                          │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                 03_calidad.py    04_tendencias.py   Power BI Desktop
                 qc_resultados    dim_tendencia      modelo estrella + DAX
```

## Plano Fabric (el diseño propuesto)

```
┌─────────────────── Fabric Workspace: ws-sunedu-ucsp ────────────────────────┐
│                                                                             │
│  Data Pipeline  pl_ingesta_tuni        ◄── schedule mensual (ver abajo)     │
│       │  consulta el catálogo de la API y dispara solo si hay periodo nuevo │
│       ▼                                                                     │
│  Lakehouse  lh_sunedu                                                       │
│    ├── Files/bronze/      *.zip + manifiesto.csv       ◄── nb_00_ingesta    │
│    ├── Tables/silver/     Delta: ingresante, matriculado, postulante        │
│    │                                              ◄── nb_01_transformar     │
│    └── Tables/gold/       Delta: dim_* y fct_*    ◄── nb_01_transformar     │
│                                  dim_tendencia_programa◄── nb_04_tendencias │
│                                  qc_resultados         ◄── nb_03_calidad    │
│                     │                                                       │
│                     ├──────────────► SQL Analytics Endpoint (T-SQL)         │
│                     │                consultas ad-hoc y validación          │
│                     ▼                                                       │
│       Modelo semántico Direct Lake  ──────►  Informe Power BI               │
│       (relaciones + las mismas medidas DAX)  (4 páginas, mismos visuales)   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                   ▲
                        TUNI.PE API (misma cadena de 5 pasos)
```

---

## Capas de datos

| Capa | Dónde | Formato | Contenido | Retención |
|---|---|---|---|---|
| **Bronze** | `Files/bronze/` | Zips tal como los publica SUNEDU | Los **9 datasets del catálogo**, 56 archivos, 1 270 MB, con manifiesto sha256 | Indefinida: es la evidencia de trazabilidad |
| **Silver** | `Tables/silver/` | Delta | **7 de los 9** tipados y normalizados, esquemas divergentes unificados, filtrados a pregrado | Última carga completa |
| **Gold** | `Tables/gold/` | Delta | Modelo estrella: **6 dimensiones conformadas + 7 hechos** + la salida estadística + los resultados de calidad | Histórico, con versionado de Delta |

Nótese que los conteos **bajan** de capa en capa, y eso es la propiedad que define el diseño: la ingesta no decide nada y el modelo decide todo. Bronze guarda lo que SUNEDU publicó, sin interpretar; silver tipa lo que tiene llave viable; gold expone lo que responde una pregunta. Las exclusiones están declaradas en `referencias/datasets.csv` y el control de calidad #13 confronta esa declaración con la base en cada corrida.

### Por qué son tres capas y no dos

La pregunta es razonable, porque silver y gold comparten contenedor —el mismo Lakehouse allí, el mismo archivo DuckDB en local— y desde fuera pueden parecer una sola. Una capa está justificada si cumple al menos una de dos condiciones: que **algo la consuma que no consuma la siguiente**, o que **la siguiente se pueda reconstruir sin reconstruir ésta**. Silver cumple las dos:

- **Consumidor propio.** Nueve de los catorce controles de calidad leen silver y no gold — tienen que, porque conciliar filas y contar duplicados solo es posible antes de agregar. Y silver contiene dos datasets que nunca llegan a gold.
- **Ciclo de vida propio.** `python 02_transformar.py --solo-gold` reconstruye las trece tablas del modelo sin volver a leer un solo CSV. Esa bandera **existe únicamente porque silver es una capa materializada aparte**; sin ella, cada ajuste a una regla de dimensión obligaría a re-parsear 17,4 millones de filas.

En Fabric esa segunda propiedad se traduce en una ventaja operativa concreta: el Pipeline puede re-ejecutar solo la actividad de gold tras un cambio en el modelo semántico, sin volver a tocar `Files/bronze/` ni gastar capacidad en re-ingestar.

### Una asimetría del plano local que en Fabric desaparece

En local, bronze y gold tienen carpeta de datos (`data/bronze/`, `data/gold/*.parquet`) y silver **no**: vive solo dentro de `data/sunedu.duckdb`. El motivo es quién la consume: nada fuera del pipeline lee silver, y los controles de calidad la leen por la misma conexión que la creó. Exportarla serían millones de filas en parquet que nadie abriría.

En Fabric la asimetría se corrige por sí sola, y es coherente con la regla: allí silver **sí** es `Tables/silver/` en Delta, porque el *SQL Analytics Endpoint* permite consultarla con T-SQL desde fuera del pipeline. Cuando aparece un consumidor externo, aparece la materialización.

### Mapeo capa por capa

| Capa | Local | Fabric | Trabajo de traducción |
|---|---|---|---|
| Ingesta | `01_descargar.py` | `nb_00_ingesta`: el mismo script, cambiando las rutas de `config.py` a `/lakehouse/default/Files/` | Mínimo: son 8 constantes |
| Landing bronze | `data/bronze/*.zip` + manifiesto | `Files/bronze/` + el mismo manifiesto | Ninguno |
| Bronze → Silver | DuckDB `read_csv` (`sql/bronze/`) | `spark.read.csv(sep='\|', encoding='windows-1252')` | **Se reescribe esta capa** |
| Silver | Tablas DuckDB (`sql/silver/`) | Delta vía `spark.sql()` | 4 líneas: las dos macros como UDF y la lectura del CSV de referencia |
| Gold | Parquet (`sql/gold/`) | Delta vía `spark.sql()` | **Ninguno: los mismos archivos, sin cambios** |
| Calidad | `03_calidad.py` + `sql/calidad.sql` | `nb_03_calidad`, escribiendo a `Tables/gold/qc_resultados` | 3 bloques `UNPIVOT` → `stack()` |
| Estadística | `04_tendencias.py` (numpy + scipy) | El mismo notebook | Ninguno |
| Capa semántica | `.pbix` import sobre Parquet | Modelo **Direct Lake** sobre `Tables/gold` | Ninguno: mismas relaciones, mismo `medidas.csx` |
| Orquestación | `run_all.py` | Data Pipeline con dependencias entre actividades | Reemplazo directo |
| SQL ad-hoc | DuckDB CLI | **SQL Analytics Endpoint** (T-SQL) | Ver `sql/portabilidad.md` |

**El trabajo de traducción está medido, no estimado:** son **5 de las 397 líneas de código** de `sql/silver/` y `sql/gold/` — el 1,3 %, y las cinco están en silver. La capa gold entera —las seis dimensiones, los siete hechos, el HHI— se ejecuta sobre Spark sin tocar una coma. El desglose por motor está en [`sql/portabilidad.md`](../sql/portabilidad.md).

Que la cifra sea 4 y no 25 es una decisión, no una casualidad: `arg_max()` se escribió como `max_by()` y el único `CAST(... AS VARCHAR)` se tipó como `VARCHAR(4)`, porque ambas formas las aceptan DuckDB y Spark por igual. Las cuatro líneas restantes son las dos macros `norm()` y `limpio()` —que en Spark son UDF de Python, verificadas contra las macros sobre los 1 299 valores distintos reales, con cero diferencias— y la lectura del CSV de macrorregiones.

Por eso el notebook de gold es este bucle y nada más:

```python
for archivo in sorted(Path("/lakehouse/default/Files/sql/gold").glob("*.sql")):
    spark.sql(archivo.read_text(encoding="utf-8"))
```

El notebook completo, con la capa bronze y el registro de las UDF, está en [`fabric/nb_01_transformar.py`](../fabric/nb_01_transformar.py). Esa es la razón de haber puesto la lógica en archivos `.sql` separados del runner de Python, y no embebida en pandas.

---

## Orquestación

Data Pipeline `pl_ingesta_tuni`, con las actividades encadenadas por dependencia de éxito:

```
[Web: catálogo de la API]
        │
        ├── ¿hay periodo nuevo? ── no ──► [Fin, sin ejecutar nada]
        │
        sí
        ▼
[nb_00_ingesta] ──► [nb_01_transformar] ──┬──► [nb_03_calidad] ─────┐
                                          │                         │
                                          └──► [nb_04_tendencias] ──┤
                                                                    ▼
                                                     ¿algún control en REVISAR?
                                                          │                │
                                                       sí │                │ no
                                                          ▼                ▼
                                               [Alerta por correo]   [Refresh del
                                                                   modelo semántico]
```

Dos decisiones de la orquestación que no son obvias:

**El refresh del modelo semántico se condiciona a que pasen los controles de calidad.** No tiene sentido publicar un dataset que no concilia. `nb_03_calidad` devuelve el conteo de controles en estado `REVISAR`; el Pipeline bifurca sobre ese valor. Es la misma lógica que ya imprime `03_calidad.py` al final de su ejecución.

**La estadística y la calidad corren en paralelo.** `nb_04_tendencias` solo depende de gold, no de calidad, así que no hay motivo para serializarlas. Con estos volúmenes la diferencia es de segundos, pero la dependencia correcta es la que hay que declarar.

---

## Actualización programada

SUNEDU publica aproximadamente cada seis meses, pero **las fechas de corte varían**. Un cron semestral a ciegas llegaría tarde a unas publicaciones y correría en vacío en otras.

**Diseño propuesto: verificación mensual con disparo condicional.** El Pipeline corre el día 1 de cada mes, consulta `POST /api/serviciotuni/listar` con una actividad Web y compara el catálogo devuelto contra el manifiesto almacenado en `Files/bronze/`. Solo si aparece un periodo que no está en el manifiesto ejecuta la rama de ingesta.

Es barato —una llamada HTTP los meses en que no hay nada nuevo—, es idempotente, y nunca llega tarde a una publicación. El mismo manifiesto con sha256 que da idempotencia en local es el que da la detección de novedad en Fabric: no hay que construir nada nuevo para esto.

**Reproceso histórico.** Si SUNEDU corrige un archivo ya publicado, el sha256 cambia y el Pipeline lo detecta como novedad aunque el periodo ya exista. Ese es el comportamiento deseado, y sale gratis por cómo está construido el manifiesto.

---

## Modelo semántico Direct Lake

Sobre `Tables/gold`, con las mismas 25 relaciones y las mismas 79 medidas: `powerbi/medidas.csx` se aplica con Tabular Editor igual que sobre el `.pbix`.

**Por qué Direct Lake y no Import.** Las tablas de hechos son pequeñas (10–16 mil filas) y ya están en Delta: Direct Lake las consulta directamente desde el lago, sin importar ni duplicar datos, y el informe refleja la última versión sin un paso de refresco del dataset. Con estos volúmenes Import también funcionaría perfectamente; Direct Lake se prefiere porque elimina un paso de la cadena y, por tanto, un punto de fallo.

**Lo que habría que vigilar.** Direct Lake recae en DirectQuery si se superan los límites de la capacidad, y el rendimiento depende de que los ficheros Delta estén compactados. Con 16 mil filas ninguno de los dos es un riesgo real, pero son las dos cosas que sí importarían si el modelo creciera al grano de local o al detalle por persona.

---

## Capacidad, seguridad y operación

**Capacidad.** El volumen de este proyecto es trivial para cualquier SKU: el gold completo pesa unos 4 MB y las trece tablas suman del orden de 80 mil filas entre todos. El consumo real estaría en el Spark de la ingesta, que procesa unos 11 GB de CSV y corre **dos veces al año**. La SKU más pequeña con Direct Lake habilitada es suficiente; el dimensionamiento no lo fija este proyecto, sino lo que la institución monte al lado. Conviene señalarlo porque la capacidad en Fabric se factura por tiempo encendido, no por uso: un workspace dedicado solo a esto estaría ocioso el 99 % del tiempo.

**Seguridad y gobierno.** Los datos son públicos y abiertos, así que no hay información sensible que proteger en este modelo. Lo que sí correspondería configurar:

- **Roles del workspace**: `Admin` para el responsable del área de datos, `Member` para quien mantiene los notebooks, `Viewer` para los consumidores del informe. El acceso al informe se concede sobre la app, no sobre el workspace.
- **RLS**: innecesaria aquí. Pasaría a ser obligatoria en el momento en que este modelo se cruce con datos internos de la UCSP —matrícula propia, notas, pagos—, y el punto natural de aplicación sería `dim_universidad`.
- **Linaje**: Fabric lo expone de forma nativa entre Lakehouse, modelo semántico e informe. Es una de las ventajas reales frente al plano local, donde la trazabilidad depende del manifiesto y de este documento.

**Monitoreo.** Alerta por correo ante fallo del Pipeline, y ante cualquier control de calidad en estado `REVISAR`. Esa segunda alerta es la que importa: un fallo de ejecución es visible, pero un pipeline que corre bien sobre datos que dejaron de conciliar es el que pasa desapercibido.

---

## Cuándo Fabric se justifica aquí, y cuándo no

Por volumen, este proyecto **no necesita Fabric**: unos 11 GB de CSV procesados dos veces al año caben en un portátil, y es exactamente lo que demuestra el plano local.

Lo que justificaría moverlo a Fabric no es el tamaño, son tres cosas de operación:

1. **Que el proceso corra sin que nadie lo lance.** Hoy depende de que alguien ejecute `run_all.py`.
2. **Que el informe se actualice solo**, y que haya una fuente única, versionada y con linaje, en vez de un `.pbix` en la máquina de alguien.
3. **Que estos datos se crucen con los internos de la UCSP.** Ese es el caso de uso real: benchmark externo contra matrícula propia. En cuanto hay dos fuentes y dos dueños, la gobernanza deja de ser opcional.

Decirlo así —y no "hay que llevarlo a Fabric porque sí"— es parte de la respuesta. El diseño está hecho para que esa migración sea barata el día que alguna de las tres razones aplique, y para no haber pagado su costo antes de tiempo.

---

## Si se montara: orden de trabajo

1. Workspace `ws-sunedu-ucsp` + Lakehouse `lh_sunedu`.
2. Subir `data/bronze/*.zip` y la carpeta `sql/` a `Files/`. Los datos ya están descargados: no hace falta repetir la descarga.
3. Importar [`fabric/nb_01_transformar.py`](../fabric/nb_01_transformar.py) como notebook y ejecutarlo. Ya trae las UDF, la lectura con `spark.read.csv` y el bucle sobre los `.sql`.
4. Portar `03_calidad.py` y `04_tendencias.py` como notebooks, escribiendo el resultado a `Tables/gold` en vez de a CSV y Parquet. Son pandas y scipy sobre tablas de 16 mil filas: no necesitan Spark.
5. Crear el modelo semántico Direct Lake, recrear las relaciones según [`powerbi/GUIA_ARMADO.md`](../powerbi/GUIA_ARMADO.md) y aplicar `medidas.csx` con Tabular Editor.
6. Armar el Pipeline con la detección mensual de periodo nuevo y la bifurcación por calidad.

Todo es montaje: el trabajo de ingeniería —la traducción de la capa de transformación— ya está hecho y entregado.
