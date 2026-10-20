# Notebooks de Microsoft Fabric (PySpark)

El diseño de la solución sobre Fabric está en [`docs/arquitectura_fabric.md`](../docs/arquitectura_fabric.md). Esta carpeta contiene el **código que lo implementa**, escrito para el runtime de Spark de Fabric.

## Por qué está aquí

El requerimiento 3.6 admite *implementar o describir* la arquitectura en Fabric, y este proyecto se entrega sin capacidad de Fabric activa — las razones están en el documento de arquitectura. Describir sin código deja la afirmación "el SQL es portable" sin respaldo: cualquiera puede dibujar un diagrama de medallion.

Estos notebooks son el respaldo. Demuestran, en código revisable, que la capa de transformación corre sobre Spark **ejecutando los mismos archivos `.sql`** que la versión local con DuckDB.

## Qué hay

| Archivo | Equivalente local | Qué hace |
|---|---|---|
| `nb_01_transformar.py` | `02_transformar.py` | Bronze → Silver → Gold sobre el Lakehouse: 7 cargadores, 6 dimensiones, 6 hechos |

El notebook carga los **siete datasets que llegan a silver**, de los nueve que la ingesta baja. Las dos exclusiones están declaradas en `referencias/datasets.csv`, que el notebook también materializa como tabla para que el control de calidad #13 pueda verificarlas.

`03_calidad.py` y `04_tendencias.py` no se duplican: son pandas, numpy y scipy sobre tablas de cientos a decenas de miles de filas, y en Fabric se ejecutan tal cual cambiando el origen de los datos. Reescribirlos en PySpark añadiría código sin añadir capacidad.

## Lo único que cambia respecto de la versión local

| | Local (DuckDB) | Fabric (Spark) |
|---|---|---|
| Lectura de planos | `read_csv(...)` dentro del SQL | `spark.read.csv()`, vista temporal |
| `norm()` y `limpio()` | `CREATE MACRO` | UDF de Python registradas con `spark.udf.register` |
| Tipos del DDL de silver | `VARCHAR` | `STRING` (Spark exige longitud en `VARCHAR`) |
| `ref_parametros` | se genera con `.format()` desde `config.py` | se escribe con los mismos valores, declarados en el encabezado del notebook: no puede importar `config.py`, que vive fuera del Lakehouse |
| **`sql/gold/*.sql`** | — | **Sin ningún cambio** |

Son **5 líneas** de las 382 de `sql/silver/` y `sql/gold/`, todas en silver. La capa gold completa —las seis dimensiones y los seis hechos— se ejecuta sin tocar una coma. Ese resultado no es casual: `arg_max()` se escribió como `max_by()` y el único `CAST(... AS VARCHAR)` se tipó como `VARCHAR(4)` precisamente para que los dos motores aceptaran el mismo texto.

## Qué está verificado y qué no

**Verificado.** Las UDF `limpio()` y `norm()` se contrastan contra las macros de DuckDB sobre **todos** los valores distintos de texto de silver —**8 763** valores de 26 campos— más un juego de casos límite: **cero diferencias**. El script es `verificar_udf.py` y se entrega; extrae las funciones del propio notebook en vez de llevar una copia, para que no puedan desincronizarse. Y los `.sql` que el notebook carga son exactamente los que produjeron las cifras entregadas.

> **Esa verificación encontró un fallo real.** La primera versión usaba 1 299 valores y daba cero diferencias. Al ampliarla a los 8 763 aparecieron **cuatro**, todas por el trato de los espacios en blanco: `trim()` de DuckDB no quita tabuladores y su `\s` no cubre el espacio duro `chr(160)`, mientras los de Python sí. **Las macros eran las que estaban mal** —dejaban pasar un espacio duro dentro de una llave de texto, y `silver_titulo.nombre_entidad` trae 588 filas con uno—. Se corrigieron las macros y se reescribieron las UDF para replicarlas.
>
> La lección es sobre el método: una verificación sobre una muestra pequeña puede dar cero diferencias y no probar nada.

**No verificado.** El notebook no se ha ejecutado, porque no hay capacidad de Fabric. Se declara así en su propio encabezado. Lo que se afirma es que el SQL es compatible y que la lógica de las UDF es equivalente, no que el notebook haya corrido de principio a fin.

Esa distinción importa: el resto del proyecto solo reporta cifras medidas, y esta parte no debe presentarse con el mismo grado de certeza.

## Cómo se montaría

1. Subir `sql/`, `referencias/` y `data/bronze/` a `Files/` del Lakehouse `lh_sunedu`.
2. Importar `nb_01_transformar.py` como notebook.
3. Ejecutarlo. Deja las tablas Delta en `Tables/`.
4. Crear el modelo semántico Direct Lake sobre `Tables/gold` con las relaciones y medidas de `UCSP_Benchmark.pbix`.

El orden completo, con el Pipeline y la actualización programada, está en el documento de arquitectura.
