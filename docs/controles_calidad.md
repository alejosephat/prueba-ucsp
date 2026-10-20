# Controles de calidad

El requerimiento 3.2 pide un mínimo de tres controles explícitos **con resultados reportados**, y documentar las claves de integración, la resolución de diferencias entre periodos y qué registros quedaron fuera.

Este documento registra los **tres controles principales**. Cada uno existe porque una fuente de SUNEDU dio un problema concreto que hubo que medir — ninguno es una comprobación genérica de libro.

Los demás son **de apoyo**: siguen ejecutándose y siguen siendo la compuerta del pipeline, pero no son lo que se presenta. La columna `grupo` de `salidas/calidad/qc_resultados.csv` hace la distinción explícita.

Todo está en una sola consulta, [`sql/calidad.sql`](../sql/calidad.sql), para que sea reejecutable tal cual en Fabric, PostgreSQL o SQL Server.

---

## Principal 1 — Nada se pierde entre capas

**Control #02 · Conciliación crudo → silver · 49 filas · todas en OK**

### El problema que lo motiva

`GYT_Nacionales_2021.csv` abortaba la carga entera. La causa estaba en **dos filas de 327 475**: la columna `PROGRAMA_ACREDITADO_SINEACE` traía el valor

```
"SI" RP.NRO.000135-2020-SINEACE/CDAH-P
```

El campo *empieza* por comilla, el parser la tomó como apertura de un campo entrecomillado, no encontró el cierre que exige la gramática CSV y descartó el archivo completo. El 0,0006 % impedía leer el 100 %.

La reacción fácil habría sido `ignore_errors=true`. Eso habría saltado las dos filas **en silencio** y nadie habría mirado nunca esa columna.

A eso se suma que el filtro de pregrado descarta en torno al 20 % de cada archivo. Entre un recorte legítimo del 20 % y una pérdida accidental no hay diferencia visible en ninguna cifra del informe.

### Qué mide

Por cada uno de los 44 archivos cargados: las filas del CSV que pasan el filtro de pregrado, contra las filas que efectivamente llegaron a la tabla de silver.

```sql
CAST(s.filas - c.filas_pregrado AS DOUBLE)   -- umbral estricto: = 0
```

El conteo del numerador se toma **en la capa bronze, antes de filtrar**, y se guarda en `silver_conteo_crudo`. Sin ese registro previo no habría contra qué conciliar.

### Resultado

**0 diferencias en los 44 archivos.** Umbral estricto, no tolerancia.

### Qué decisión sostiene

Que `quote=''` en los siete cargadores fue la corrección correcta y no un parche: si hubiera descartado filas, este control lo diría. Y que `ignore_errors=false` se mantiene en todo el pipeline — un error ruidoso que obliga a entender el formato es preferible a una pérdida silenciosa.

---

## Principal 2 — Las llaves identifican lo que dicen identificar

**Control #05 · Integridad referencial · 17 verificaciones · todas en OK**

### El problema que lo motiva

Cuatro rarezas medidas en las fuentes, cada una capaz de dejar filas sin pareja en su dimensión:

| Lo que trae la fuente | Lo que rompería |
|---|---|
| `CODIGO_SIU_PROGRAMA` **no es único a nivel nacional**: 288 de 471 códigos se repiten entre universidades | Usarlo solo fusionaría programas de universidades distintas, sin error visible |
| `DEPARTAMENTO_FILIAL` de egresados viene **vacío en el 100 %** de sus 587 527 filas | `md5(norm(departamento) ‖ …)` daría `NULL` y el hecho entero quedaría huérfano |
| `PERIODO_EGRESO` trae periodos **3 y 4** (0,43 %) y 0,78 % vacíos | 7 126 filas sin pareja en una `dim_semestre` de dos filas |
| Grados y títulos no trae `CODIGO_INEI`, sino `CODIGO_ENTIDAD = '065'` | El hecho no podría relacionarse con `dim_universidad` |

> **Por qué una fila huérfana es peligrosa.** Al relacionar dos tablas, una fila cuyo valor de llave no existe en la dimensión no encuentra pareja. En Power BI **desaparece de cualquier visual que use un campo de esa dimensión**, y lo hace sin aviso. No es un error: es una ausencia.

### Qué mide

Diecisiete verificaciones `LEFT JOIN … WHERE dim.llave IS NULL`, una por cada relación del modelo, más las ubicaciones sin macrorregión asignada.

### Resultado

**0 huérfanos en las 17 verificaciones.**

### Qué decisión sostiene

Las cuatro decisiones de modelado que resolvieron esas rarezas:

- la **llave compuesta** `md5(codigo_inei ‖ '-' ‖ codigo_siu_programa)` (decisión D1);
- declarar que `fct_egresados` **no se relaciona** con `dim_ubicacion` en vez de imputar la sede de la universidad, que para las multi-filial sería inventar geografía (D7);
- la **tercera fila `'Otro'`** de `dim_semestre`, que recoge los periodos irregulares para que esas 7 126 filas sean visibles en vez de desaparecer (D2);
- resolver la universidad de los títulos por **igualdad de nombre normalizado**, con su tasa publicada en el control #11 (97,74 %), y **no** bajar al grano de programa, que sí exigiría *fuzzy matching* sobre 2 438 nombres.

Si cualquiera de esas decisiones fuera incorrecta, este control saldría en `REVISAR` y detendría la orquestación.

---

## Principal 3 — Cada fuente cubre lo que dice cubrir

**Controles #16 y #17 · 36 filas · informativos**

### El problema que lo motiva

Este control nació persiguiendo un número imposible. La medida de titulación daba **206 %** para la UCSP: se titulaba más del doble de la gente que egresaba.

Al medir aparecieron dos causas, y ninguna era un fallo del pipeline:

**SUNEDU publica un periodo en cuanto lo tiene, no cuando está cerrado.** El último periodo de cada fuente semestral viene a medias.

**No todas las universidades reportan todos los datasets.** El de egresados cubre 132 universidades; el de matriculados, 144.

### Qué mide

**#16 — Volumen del periodo sobre la mediana de su fuente.** Compara cada periodo con la mediana de los demás de la misma fuente.

| Periodo | % de la mediana |
|---|---|
| `egresado 2025-II` | **55,2 %** |
| `docente 2025-II` | **62,5 %** |
| Todos los demás | 81 – 165 % |

**#17 — Universidades que reportan matrícula pero no egresados.**

| Año | Universidades |
|---|---|
| 2022 | 19 |
| 2023 | 17 |
| 2024 | 23 |
| 2025 | **43** |

El salto de 2025 confirma por segunda vía que el año está a medias.

### Por qué son informativos y no tienen umbral

La fuente no declara si un periodo está cerrado. Poner un umbral sería inventarlo. Lo que el control publica es el dato; la decisión de qué hacer con él es del analista, y queda escrita.

### Qué decisión sostiene

Tres, y las tres se tomaron por este control:

1. **La medida se renombró.** `Tasa de Titulacion` pasó a `Titulados por Egresado`. Una *tasa* promete que el numerador es un subconjunto del denominador; con coberturas distintas y rezago de cohorte, no lo es. Ver decisión F8.
2. **La tarjeta del dashboard pasó a ser un volumen.** La página 4 muestra `Personas Tituladas`, no un cociente. Una tarjeta KPI es el peor sitio para un número con dos confusiones: el formato promete una conclusión que el dato no soporta.
3. **Las cifras que dependen de egresados se calculan sobre el último año completo**, y el año se declara en el título del visual.

---

## Los controles de apoyo

Trece más, en el mismo `sql/calidad.sql`. No se presentan, pero se ejecutan en cada corrida y forman la compuerta del pipeline.

| # | Control | Qué aporta |
|---|---|---|
| 01 | Efecto del filtro de pregrado | Cuantifica el recorte declarado, archivo por archivo |
| 03 | Duplicados absorbidos por el `DISTINCT` | Mide cuántos absorbe el conteo de personas distintas |
| 04 | Nulos en campos clave | 0 en los obligatorios; `nombre_grupo_3` queda como INFO (limitación declarada de la fuente) |
| 06 | Matrícula sin ingresantes | Programas en posible extinción, pedido explícito del enunciado |
| 07 | Cobertura de periodos | Abierto por licenciamiento SUNEDU: las series truncadas son cierres reales, no fallas |
| 08 | Variación intra-anual (II vs I) | Retención dentro del año, en los seis años |
| 09 | Conciliación cruzada entre fuentes | Admitidos contra ingresantes: dos datasets independientes que concuerdan |
| 10 | Universidades con nombre divergente | Resueltas por código INEI |
| 11 | Títulos resueltos por nombre | **97,74 %** — decide si `fct_titulos` es usable |
| 12 | Carnés emitidos sobre matriculados | Contraste contra una fuente independiente |
| 13 | Triaje de datasets: declarado vs real | Confronta `referencias/datasets.csv` con la base |
| 14 | Variación interanual de la matrícula | Evidencia para excluir 2020 de la regresión |
| 15 | El `GUID` de carnés identifica personas | **No**: 658 filas por valor distinto. Es un identificador de lote |

### Por qué no se borraron

Cuatro de ellos detectaron defectos reales durante la construcción: el #12 llevó al #15 y al hallazgo del GUID de lote; el #16 llevó a renombrar la medida de titulación; el #02 validó la corrección del `quote=''`; el #11 decidió que un hecho entero fuera usable.

Un control que ya encontró un bug es barato de mantener y caro de volver a escribir. Lo que se corrigió no fue su existencia sino **qué se presenta**: tres, atados a problemas medidos, con su sustento escrito.

---

## Tres estados, no dos

| Estado | Significa |
|---|---|
| `OK` | Hay un umbral y se cumple |
| `INFO` | No hay un valor correcto conocido: declarar un umbral sería inventarlo |
| `REVISAR` | Hay un umbral y no se cumple. **Detiene la orquestación** |

La distinción no es cosmética. En el Pipeline de Fabric la actividad de calidad es una **compuerta**: si algo sale en `REVISAR`, el refresco del modelo semántico no se ejecuta. Un control permanentemente en rojo por una limitación conocida de la fuente —como el ~20 % de registros sin clasificación CINE— volvería inservible esa compuerta, y el equipo aprendería a ignorarla.

**Resultado de la última corrida: 106 filas en OK, 116 informativas, 0 en REVISAR.**
