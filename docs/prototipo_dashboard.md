# Prototipo del dashboard

Tres páginas ejecutivas para la dirección universitaria. Cada una responde una pregunta de gestión, y su primera línea es un **titular calculado en DAX** que se reescribe con los filtros.

Las imágenes son la maqueta dibujada con las cifras reales del modelo. La especificación visual por visual (posición, campos y formato) está en [`powerbi/GUIA_ARMADO.md`](../powerbi/GUIA_ARMADO.md).

## 1 · Posición de mercado (pregunta 4.1)

![Página 1](img/tablero_p1.png)

**Pregunta:** ¿cómo evolucionan la oferta y la matrícula de la UCSP frente al sur y al país?

**Lectura:** la matrícula crece 0,8 % al año porque arrastra cohortes; el **ingreso cae 4,9 %** mientras el del sur sube 8,2 %. Las dos líneas indexadas son la respuesta; las fichas dan el último año, su variación y la referencia del mercado.

## 2 · Portafolio de programas (preguntas 4.2 y 4.3)

![Página 2](img/tablero_p2.png)

**Pregunta:** ¿qué programas sostienen la demanda y cuáles la arriesgan?

**Mitad izquierda:** los top y bottom 5 del año responden a universidad, departamento, gestión y año.

**Mitad derecha:** la tendencia de cada programa de la UCSP, contra la de su mismo campo CINE en el sur. La diagonal separa los programas que ganan cuota de los que la pierden.

**Lectura:** ningún programa crece en ingreso y matrícula a la vez. Dos caen en ambas series y uno ya pierde ingreso.

## 3 · Admisión y selectividad (pregunta 4.4)

![Página 3](img/tablero_p3.png)

**Pregunta:** ¿qué tan selectiva es la UCSP frente a sus pares privados del sur?

**Lectura:** admite el 56 % contra el 77 % de las privadas. La caída desde el 76 % de 2024 es de composición: **Medicina Humana** abre con 1 715 postulaciones y admite el 6 %. Sin ella, la tasa es del 79 %.

## Principios de diseño

| Principio | Cómo se aplica |
|---|---|
| Una frase arriba que responde | `Titular Resumen`, `Titular Tendencia`, `Titular Selectividad`: medidas de texto que cambian con los filtros |
| Énfasis, no arcoíris | UCSP en azul `#2A78D6`; sur y país en grises, con etiqueta directa al final de cada línea |
| Un solo eje | Las series de escalas distintas se indexan a base 100 en lugar de usar dos ejes |
| Fichas con contexto | Último año, variación contra el anterior y la referencia del mercado |
| El estado se lee en la forma | Lectura de cada programa con ícono y color de estado, nunca solo color |
| Comparadores justos | Selectividad contra las privadas del sur; las públicas solo como contexto |
| Filtros en una fila arriba | Periodo, departamento, macrorregión sur y gestión, sincronizados |
