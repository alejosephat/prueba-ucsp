# Preguntas e indicadores

El enunciado no pide usar todos los indicadores que sugiere: valora seleccionar los que permiten responder. Este documento registra la selección para cada pregunta, lo que se descartó y por qué.

Una regla atraviesa todas las páginas: **la UCSP siempre se lee contra un comparador**, sea la macrorregión sur, el país o su mismo campo de estudio. Un número de la UCSP aislado no dice si es bueno o malo.

---

## Definiciones que usan las cuatro preguntas

**Macrorregión sur.** Ocho departamentos:

- Arequipa
- Cusco
- Puno
- Moquegua
- Tacna
- Apurímac
- Ayacucho
- Madre de Dios

Es el sur andino más la selva sur, según el agrupamiento usado por INEI y CEPLAN. Ica queda fuera porque suele asociarse al centro-sur. La definición vive en `referencias/macrorregiones.csv`: cambiarla es editar una línea.

**Programas equivalentes.** Se homologan por la clasificación **CINE-UNESCO** que SUNEDU ya publica en la fuente: 83 campos detallados (`nombre_grupo_3`). Es el criterio oficial del regulador. Evita emparejar por similitud 2 438 nombres de programa distintos, donde cualquier umbral sería arbitrario. Los 13 programas de la UCSP tienen su campo asignado.

**Comparadores justos.** Las series del sur y del país respetan los filtros de periodo, programa y **gestión**. Ignoran la universidad y la ubicación, que son las que definen cada grupo. En selectividad, el comparador por defecto son las **demás privadas del sur**: las públicas admiten entre 13 % y 15 % de las postulaciones y arrastran cualquier promedio que las incluya.

---

## 4.1 · Benchmark de demanda

*¿Cómo evolucionaron la oferta académica y la matrícula por programa de la UCSP frente a su región y al país?*

| Indicador elegido | Medida | Por qué |
|---|---|---|
| Ingresantes y matrícula en base 100 | `Indice Ingresantes *`, `Indice Matricula *` | La UCSP tiene 9 188 matriculados y el país 1,55 millones. Indexadas, las tres series comparten un eje |
| Crecimiento anual compuesto de la UCSP, el sur y el país | `CAGR Ingresantes *`, `CAGR Matricula *` | Resume la evolución del rango en una cifra comparable |
| Cuota de la matrícula del sur | `Cuota de Mercado en el Sur` | Dice directamente si la UCSP gana o pierde peso en su región |
| Participación de cada programa | `% Participacion en su Universidad` | Es la "distribución de la matrícula por programa" que pide la pregunta |
| Programas activos | `Programas Activos` | Es la "cantidad de programas" del enunciado |
| Alumnos por docente (contexto) | `Ratio Alumno Docente *` | Es una condición básica de calidad del licenciamiento; ubica el tamaño frente a la capacidad |

| Descartado | Por qué |
|---|---|
| Matrícula en valores absolutos, lado a lado | La escala hace ilegible a la UCSP junto al país |
| Número de universidades | Describe el sistema, no a la UCSP |
| Índice de concentración (HHI) | Resume la distribución en un número que hay que explicar antes de leerlo; las barras de participación la muestran directamente |

**Lo que muestra:** en 2021–2025 la matrícula de la UCSP crece 0,8 % al año, pero su **ingreso cae 4,9 %** mientras el del sur sube 8,2 % y el de las privadas del sur 12,6 %. La matrícula todavía crece porque arrastra cohortes de años anteriores.

## 4.2 · Demanda por programa

*¿Cuáles son los 5 programas con mayor y menor ingreso y matrícula por año, según los filtros?*

| Indicador elegido | Medida | Por qué |
|---|---|---|
| Top 5 por ingreso y por matrícula | `Ranking Programa`, `Ranking Programa (Ingresantes)` | `ALLSELECTED` recalcula el ranking con universidad, departamento, gestión y año |
| Bottom 5 por ingreso y por matrícula | `Ranking Programa Inverso`, `Ranking Programa Inverso (Ingresantes)` | Excluye programas con menos de 10 alumnos, que de otro modo ocuparían siempre el fondo |

| Descartado | Por qué |
|---|---|
| Un parámetro de campo para alternar la métrica | Un ranking propio por métrica es más claro: el ordenamiento debe seguir a la métrica que se muestra |

**Lo que muestra (UCSP, 2025):** mayor ingreso, Ingeniería Industrial (483); menor, Contabilidad (65).

## 4.3 · Tendencia de los programas

*¿Qué programas de la UCSP muestran una tendencia sostenida de crecimiento o caída, y cómo se compara con sus equivalentes del sur?*

| Indicador elegido | Medida | Por qué |
|---|---|---|
| Tendencia por regresión del ingreso y de la matrícula | `CAGR OLS Ingresantes`, `CAGR OLS Matricula` | Usa los cinco puntos de la serie y da significancia. Detalle en [`componente_estadistico.md`](componente_estadistico.md) |
| Lectura cruzada de las dos series | `dim_tendencia_programa[lectura]` | La matrícula de un programa nuevo crece aunque su ingreso caiga; manda el ingreso |
| Tendencia del mismo campo CINE en el sur, sin la UCSP | `CAGR Campo Sur Ingresantes` | Separa "cae el mercado" de "pierde competitividad" |
| Programas confirmados, en caída y en alerta | `Programas Crecimiento Confirmado` y siguientes | Es la respuesta en tres números |

| Descartado | Por qué |
|---|---|
| CAGR entre el primer y el último año | Usa 2 de 5 puntos: un año atípico en un extremo cambia el signo |
| Tendencia solo de la matrícula | Habría reportado como "crecimiento sostenido" a programas cuyo ingreso cae |

**Lo que muestra:** ningún programa de la UCSP crece en las dos series. Contabilidad y Administración caen en ambas; Arquitectura ya pierde ingreso aunque su matrícula todavía sube. El ingreso pierde cuota frente a su campo en el sur en 11 de 12 programas.

## 4.4 · Pregunta adicional: selectividad

*¿Qué tan selectiva es la admisión de la UCSP frente a sus pares del sur, y cómo evolucionó en 2022–2025?*

**Por qué esta pregunta.** Postulantes comparte las mismas llaves que ingresantes y matrícula, así que se integra al mismo modelo sin tablas puente. Además responde una duda que una oficina de admisión se hace de verdad: si los programas que crecen lo hacen captando demanda o bajando la exigencia.

| Indicador elegido | Medida | Por qué |
|---|---|---|
| Tasa de admisión de la UCSP | `Tasa de Admision UCSP` | Admitidos sobre postulaciones, ambos de la misma fuente |
| La misma tasa en las privadas y en las públicas del sur | `Tasa de Admision Privadas del Sur`, `... Publicas del Sur` | El comparador justo y su contexto |
| Tasa por campo de estudio | las mismas, por `campo_estudio` | El agregado mezcla programas de exigencia muy distinta |
| Embudo de admisión | `Postulaciones`, `Admitidos`, `Ingresantes` | El mismo año y las mismas personas: no mezcla cohortes |
| Selectividad frente a la tendencia del ingreso | dispersión por programa | Responde si se crece captando demanda o abriendo la puerta |

| Descartado | Por qué |
|---|---|
| Comparar con el sur completo | Con las públicas, la UCSP parece menos selectiva; contra sus pares privados lo es más |
| Egresados y títulos en el embudo | Son otras cohortes, con años de rezago: el embudo dejaría de describir a las mismas personas |

**Lo que muestra:** en 2025 la UCSP admite el 56 % de sus postulaciones, contra el 77 % de las privadas del sur. Pero la caída desde el 76 % de 2024 la explica **Medicina Humana**, que abre en 2025 con 1 715 postulaciones y admite el 6 %. Sin ella, la tasa es del 79 % y las postulaciones caen 12,7 %.
