// Script de Tabular Editor: crea todas las medidas del modelo.
//
// Uso:
//   1. Abrir el .pbix en Power BI Desktop con el modelo ya cargado y relacionado.
//   2. Herramientas externas -> Tabular Editor.
//   3. Pestana C# Script, pegar este archivo, F5.
//   4. Volver a Power BI Desktop y guardar.
//
// Generado por 05_powerbi.py. No editar a mano: editar la lista MEDIDAS de ese
// script y volver a generarlo, para que el catalogo documentado no se desincronice.

// Las medidas viven en una tabla propia, no colgadas de un hecho: el panel de
// campos queda limpio y los hechos pueden ocultarse enteros.
var tabla = Model.Tables.Contains("_Medidas")
    ? Model.Tables["_Medidas"]
    : Model.AddCalculatedTable("_Medidas", "ROW ( \"Medidas\", BLANK () )");

// Columna de ayuda para el filtro de pagina de la pregunta 4.3: el segmentador
// de universidad no llega a dim_programa, porque las dimensiones no se
// relacionan entre si.
var programa = Model.Tables["dim_programa"];
if (!programa.Columns.Contains("es_ucsp"))
    programa.AddCalculatedColumn("es_ucsp",
        "LOOKUPVALUE ( dim_universidad[es_ucsp], dim_universidad[codigo_inei], dim_programa[codigo_inei] )");

Measure m;


m = tabla.AddMeasure("Ingresantes", "SUM ( fct_ingresantes[ingresantes] )");
m.DisplayFolder = "01 Base";
m.FormatString = "#,0";
m.Description = "Personas distintas que ingresan a un programa de pregrado en el anio.";

m = tabla.AddMeasure("Matriculados", "-- La matricula es un STOCK: la misma persona aparece en cada semestre y en\n-- cada anio que sigue estudiando. Por eso esta medida no es un SUM, en dos ejes:\n--\n--   Semestre. fct_matricula trae los 12 semestres de 2020-I a 2025-II. Se fija\n--   el marcado en dim_semestre[es_serie_anual]: sumar I y II contaria dos veces\n--   a quien estudio todo el anio. El REMOVEFILTERS hace falta ademas del\n--   filtro, para que una seleccion del slicer de semestre no se intersecte.\n--\n--   Anio. Con varios anios en contexto (una tarjeta sin filtro de periodo, la\n--   fila de total de una tabla) devuelve el ULTIMO anio con dato: sumar\n--   2021-2025 contaria a la misma persona hasta cinco veces.\nVAR UltimoAnio =\n    CALCULATE (\n        MAX ( fct_matricula[anio] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[es_serie_anual] = TRUE\n    )\nRETURN\n    CALCULATE (\n        SUM ( fct_matricula[matriculados] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[es_serie_anual] = TRUE,\n        dim_periodo[anio] = UltimoAnio\n    )");
m.DisplayFolder = "01 Base";
m.FormatString = "#,0";
m.Description = "Personas distintas matriculadas en pregrado en la serie anual comparable (un semestre fijo por anio). Es un stock: con varios anios en contexto devuelve el del ULTIMO anio, no la suma. El slicer de semestre no la afecta: para eso esta [Matriculados Semestre].";

m = tabla.AddMeasure("Ingresantes Ultimo Anio", "VAR UltimoAnio = MAX ( fct_ingresantes[anio] )\nRETURN\n    CALCULATE ( [Ingresantes], dim_periodo[anio] = UltimoAnio )");
m.DisplayFolder = "01 Base";
m.FormatString = "#,0";
m.Description = "Ingresantes del ULTIMO anio del contexto. [Ingresantes] es un flujo y suma el rango, que es lo correcto en una serie; esta es la cifra de la ficha.";

m = tabla.AddMeasure("Postulaciones", "SUM ( fct_postulantes[postulaciones] )");
m.DisplayFolder = "01 Base";
m.FormatString = "#,0";
m.Description = "Postulaciones recibidas (una persona puede postular a varios programas).";

m = tabla.AddMeasure("Postulantes", "SUM ( fct_postulantes[postulantes] )");
m.DisplayFolder = "01 Base";
m.FormatString = "#,0";
m.Description = "Personas distintas que postulan. Menor que Postulaciones por multipostulacion.";

m = tabla.AddMeasure("Admitidos", "SUM ( fct_postulantes[admitidos] )");
m.DisplayFolder = "01 Base";
m.FormatString = "#,0";
m.Description = "Postulaciones que resultaron en ingreso, segun la propia fuente de postulantes.";

m = tabla.AddMeasure("Programas Activos", "-- El filtro de semestre va por la misma razon que en [Matriculados]. Y es un\n-- stock: con varios anios en contexto cuenta los programas activos del ultimo\n-- anio, no los que tuvieron matricula en algun anio del rango. Medido: sin\n-- esta regla, la tarjeta nacional decia 2 680 programas en 2021-2025.\nVAR UltimoAnio =\n    CALCULATE (\n        MAX ( fct_matricula[anio] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[es_serie_anual] = TRUE\n    )\nRETURN\n    CALCULATE (\n        DISTINCTCOUNT ( fct_matricula[programa_sk] ),\n        fct_matricula[matriculados] > 0,\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[es_serie_anual] = TRUE,\n        dim_periodo[anio] = UltimoAnio\n    )");
m.DisplayFolder = "01 Base";
m.FormatString = "#,0";
m.Description = "Programas con matricula mayor a cero en el ULTIMO anio del contexto.";

m = tabla.AddMeasure("Matriculados AA", "VAR AnioActual = MAX ( dim_periodo[anio] )\nRETURN\n    CALCULATE (\n        [Matriculados],\n        REMOVEFILTERS ( dim_periodo ),\n        dim_periodo[anio] = AnioActual - 1\n    )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "#,0";
m.Description = "Matriculados del anio anterior. BLANK si el anio previo no esta en la serie.";

m = tabla.AddMeasure("Var. Matricula (abs)", "-- Las dos puntas se fijan a un anio concreto. Con varios anios en contexto\n-- (la fila de total) la medida devuelve la variacion del ULTIMO anio contra\n-- el anterior. Sin fijar la punta actual, en [Ingresantes] -que es un flujo y\n-- si se suma- la fila de total compararia todo el rango contra un solo anio.\nVAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior = [Matriculados AA]\nRETURN\n    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), Actual - Anterior )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+#,0;-#,0;0";
m.Description = "Diferencia absoluta de matriculados contra el anio anterior. Con varios anios en contexto, la del ultimo.";

m = tabla.AddMeasure("Var. Matricula (%)", "VAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior = [Matriculados AA]\nRETURN\n    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "Variacion porcentual de matriculados contra el anio anterior. Con varios anios en contexto, la del ultimo.";

m = tabla.AddMeasure("Ingresantes AA", "VAR AnioActual = MAX ( dim_periodo[anio] )\nRETURN\n    CALCULATE (\n        [Ingresantes],\n        REMOVEFILTERS ( dim_periodo ),\n        dim_periodo[anio] = AnioActual - 1\n    )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "#,0";
m.Description = "Ingresantes del anio anterior.";

m = tabla.AddMeasure("Var. Ingresantes (abs)", "VAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior = [Ingresantes AA]\nRETURN\n    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), Actual - Anterior )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+#,0;-#,0;0";
m.Description = "Diferencia absoluta de ingresantes contra el anio anterior. Con varios anios en contexto, la del ultimo.";

m = tabla.AddMeasure("Var. Ingresantes (%)", "VAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior = [Ingresantes AA]\nRETURN\n    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "Variacion porcentual de ingresantes contra el anio anterior. Con varios anios en contexto, la del ultimo.";

m = tabla.AddMeasure("Var. Cuota del Sur (pp)", "VAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [Cuota de Mercado en el Sur], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior =\n    CALCULATE ( [Cuota de Mercado en el Sur], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )\nRETURN\n    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) * 100 )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+0.00" pp";-0.00" pp";0.00" pp"";
m.Description = "Cambio de la cuota de la matricula del sur contra el anio anterior, en puntos porcentuales.";

m = tabla.AddMeasure("Var. Programas Activos", "VAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [Programas Activos], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior =\n    CALCULATE ( [Programas Activos], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )\nRETURN\n    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+0;-0;0";
m.Description = "Programas activos del ultimo anio menos los del anio anterior.";

m = tabla.AddMeasure("Var. HHI", "VAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [HHI Universidad], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior =\n    CALCULATE ( [HHI Universidad], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )\nRETURN\n    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+#,0;-#,0;0";
m.Description = "Cambio del HHI contra el anio anterior. Negativo = la matricula se diversifica.";

m = tabla.AddMeasure("Var. Tasa de Admision UCSP (pp)", "VAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [Tasa de Admision UCSP], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior =\n    CALCULATE ( [Tasa de Admision UCSP], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )\nRETURN\n    IF ( NOT ISBLANK ( Actual ) && NOT ISBLANK ( Anterior ), ( Actual - Anterior ) * 100 )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+0.0" pp";-0.0" pp";0.0" pp"";
m.Description = "Cambio de la tasa de admision de la UCSP contra el anio anterior, en puntos porcentuales.";

m = tabla.AddMeasure("Var. Postulaciones (%)", "VAR AnioActual = MAX ( dim_periodo[anio] )\nVAR Actual =\n    CALCULATE ( [Postulaciones], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual )\nVAR Anterior =\n    CALCULATE ( [Postulaciones], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioActual - 1 )\nRETURN\n    IF ( NOT ISBLANK ( Actual ), DIVIDE ( Actual - Anterior, Anterior ) )");
m.DisplayFolder = "02 Variacion interanual";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "Variacion porcentual de las postulaciones contra el anio anterior.";

m = tabla.AddMeasure("% Participacion en su Universidad", "VAR MatriculaPrograma = [Matriculados]\n-- La universidad del programa en contexto, capturada ANTES de quitar el filtro.\n-- dim_programa[codigo_inei] es atributo descriptivo, no llave foranea, asi que\n-- se traslada a dim_universidad con TREATAS. Sin esto, REMOVEFILTERS por si solo\n-- dejaria el denominador en el total nacional cuando no hay universidad filtrada.\nVAR SuUniversidad = VALUES ( dim_programa[codigo_inei] )\nVAR MatriculaUniversidad =\n    CALCULATE (\n        [Matriculados],\n        REMOVEFILTERS ( dim_programa ),\n        TREATAS ( SuUniversidad, dim_universidad[codigo_inei] )\n    )\nRETURN\n    DIVIDE ( MatriculaPrograma, MatriculaUniversidad )");
m.DisplayFolder = "03 Participacion";
m.FormatString = "0.0%";
m.Description = "Peso del programa dentro de la matricula de SU universidad. El denominador quita el filtro de programa pero reimpone la universidad a la que pertenece el programa del contexto, para que no se escape al total nacional.";

m = tabla.AddMeasure("Ranking Programa", "IF (\n    NOT ISBLANK ( [Matriculados] ),\n    RANKX (\n        ALLSELECTED ( dim_programa[nombre_programa] ),\n        [Matriculados],\n        ,\n        DESC,\n        DENSE\n    )\n)");
m.DisplayFolder = "04 Ranking";
m.FormatString = "#,0";
m.Description = "Posicion del programa por matricula. ALLSELECTED (no ALL) hace que el ranking se recalcule dentro de los filtros activos de universidad, departamento, gestion y periodo.";

m = tabla.AddMeasure("Ranking Programa (Ingresantes)", "IF (\n    NOT ISBLANK ( [Ingresantes] ),\n    RANKX (\n        ALLSELECTED ( dim_programa[nombre_programa] ),\n        [Ingresantes],\n        ,\n        DESC,\n        DENSE\n    )\n)");
m.DisplayFolder = "04 Ranking";
m.FormatString = "#,0";
m.Description = "Posicion del programa por ingresantes, tambien sensible a los filtros.";

m = tabla.AddMeasure("Ranking Programa Inverso", "VAR Umbral = 10\nRETURN\n    IF (\n        [Matriculados] >= Umbral,\n        RANKX (\n            FILTER ( ALLSELECTED ( dim_programa[nombre_programa] ), [Matriculados] >= Umbral ),\n            [Matriculados],\n            ,\n            ASC,\n            DENSE\n        )\n    )");
m.DisplayFolder = "04 Ranking";
m.FormatString = "#,0";
m.Description = "Posicion desde la cola, para el bottom-5. Excluye programas por debajo del umbral minimo: sin eso el fondo lo ocupan programas que abrieron ese anio con 2 o 3 alumnos y el visual deja de ser informativo.";

m = tabla.AddMeasure("Ranking Programa Inverso (Ingresantes)", "VAR Umbral = 10\nRETURN\n    IF (\n        [Ingresantes] >= Umbral,\n        RANKX (\n            FILTER ( ALLSELECTED ( dim_programa[nombre_programa] ), [Ingresantes] >= Umbral ),\n            [Ingresantes],\n            ,\n            ASC,\n            DENSE\n        )\n    )");
m.DisplayFolder = "04 Ranking";
m.FormatString = "#,0";
m.Description = "Posicion desde la cola por ingresantes, para el bottom-5 de ingreso. Mismo umbral minimo que [Ranking Programa Inverso].";

m = tabla.AddMeasure("CAGR Matricula", "VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )\nVAR AnioIni = MINX ( AniosVisibles, dim_periodo[anio] )\nVAR AnioFin = MAXX ( AniosVisibles, dim_periodo[anio] )\nVAR Saltos = AnioFin - AnioIni\nVAR ValorIni =\n    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioIni )\nVAR ValorFin =\n    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioFin )\nRETURN\n    IF (\n        Saltos > 0 && ValorIni > 0 && ValorFin > 0,\n        ( ValorFin / ValorIni ) ^ DIVIDE ( 1, Saltos ) - 1\n    )");
m.DisplayFolder = "05 Crecimiento";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "Tasa de crecimiento anual compuesta de la matricula entre el primer y el ultimo anio seleccionados. BLANK si hay un solo anio o si el inicio es cero.";

m = tabla.AddMeasure("CAGR Ingresantes", "VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )\nVAR AnioIni = MINX ( AniosVisibles, dim_periodo[anio] )\nVAR AnioFin = MAXX ( AniosVisibles, dim_periodo[anio] )\nVAR Saltos = AnioFin - AnioIni\nVAR ValorIni =\n    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioIni )\nVAR ValorFin =\n    CALCULATE ( [Ingresantes], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioFin )\nRETURN\n    IF (\n        Saltos > 0 && ValorIni > 0 && ValorFin > 0,\n        ( ValorFin / ValorIni ) ^ DIVIDE ( 1, Saltos ) - 1\n    )");
m.DisplayFolder = "05 Crecimiento";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "Tasa de crecimiento anual compuesta de los ingresantes del rango seleccionado.";

m = tabla.AddMeasure("Crecimiento Acumulado %", "VAR AniosVisibles = ALLSELECTED ( dim_periodo[anio] )\nVAR AnioIni = MINX ( AniosVisibles, dim_periodo[anio] )\nVAR AnioFin = MAXX ( AniosVisibles, dim_periodo[anio] )\nVAR ValorIni =\n    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioIni )\nVAR ValorFin =\n    CALCULATE ( [Matriculados], REMOVEFILTERS ( dim_periodo ), dim_periodo[anio] = AnioFin )\nRETURN\n    DIVIDE ( ValorFin - ValorIni, ValorIni )");
m.DisplayFolder = "05 Crecimiento";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "Variacion total de la matricula entre el primer y el ultimo anio seleccionados.";

m = tabla.AddMeasure("Matricula UCSP", "-- ALLEXCEPT y no REMOVEFILTERS ( dim_universidad ): el comparador debe\n-- respetar la gestion. Medido en 2025, la UCSP admite el 56 % de las\n-- postulaciones; el resto del sur, el 34 %; las privadas del sur, el 77 %.\n-- Contra el sur completo -arrastrado por las publicas, que admiten 13-15 %-\n-- la UCSP parece menos selectiva; contra sus pares privados lo es mas. Un\n-- comparador que ignora la gestion invierte la conclusion, y la gestion es\n-- ademas un filtro obligatorio del enunciado.\nCALCULATE (\n    [Matriculados],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_universidad[es_ucsp] = TRUE\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0";
m.Description = "Serie de referencia: matricula de la UCSP. Como todos los comparadores, ignora la universidad y la ubicacion (lo que define la cohorte) y respeta periodo, programa y gestion, que es lo que hace comparables las series.";

m = tabla.AddMeasure("Matricula Macrosur", "CALCULATE (\n    [Matriculados],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_ubicacion[es_macrosur] = TRUE\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0";
m.Description = "Matricula IMPARTIDA en locales de la macrorregion sur, sea cual sea la sede de la universidad. Es un concepto distinto de es_macrosur_sede, que clasifica a la universidad entera: una universidad de Lima con filial en Cusco aporta a esta medida, pero no cuenta como universidad del sur.";

m = tabla.AddMeasure("Matricula Nacional", "CALCULATE (\n    [Matriculados],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion )\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0";
m.Description = "Serie de referencia: matricula nacional. Ignora universidad y ubicacion y respeta periodo, programa y gestion, igual que las otras dos series del grupo, para que las tres sean comparables.";

m = tabla.AddMeasure("Indice Matricula UCSP", "VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )\nVAR Serie = [Matricula UCSP]\nVAR Base =\n    CALCULATE (\n        [Matricula UCSP],\n        REMOVEFILTERS ( dim_periodo ),\n        dim_periodo[anio] = AnioBase\n    )\nRETURN\n    DIVIDE ( Serie, Base ) * 100");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0.0";
m.Description = "Matricula de la UCSP en base 100 del primer anio seleccionado. La indexacion es lo que hace comparables tres series de escalas muy distintas (UCSP ~8 mil, sur ~200 mil, nacional ~1.6 millones) en un mismo grafico.";

m = tabla.AddMeasure("Indice Matricula Macrosur", "VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )\nVAR Serie = [Matricula Macrosur]\nVAR Base =\n    CALCULATE (\n        [Matricula Macrosur],\n        REMOVEFILTERS ( dim_periodo ),\n        dim_periodo[anio] = AnioBase\n    )\nRETURN\n    DIVIDE ( Serie, Base ) * 100");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0.0";
m.Description = "Matricula de la macrorregion sur en base 100 del primer anio seleccionado.";

m = tabla.AddMeasure("Indice Matricula Nacional", "VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )\nVAR Serie = [Matricula Nacional]\nVAR Base =\n    CALCULATE (\n        [Matricula Nacional],\n        REMOVEFILTERS ( dim_periodo ),\n        dim_periodo[anio] = AnioBase\n    )\nRETURN\n    DIVIDE ( Serie, Base ) * 100");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0.0";
m.Description = "Matricula nacional en base 100 del primer anio seleccionado.";

m = tabla.AddMeasure("CAGR Matricula UCSP", "CALCULATE (\n    [CAGR Matricula],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_universidad[es_ucsp] = TRUE\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR de la matricula de la UCSP en el rango de anios seleccionado.";

m = tabla.AddMeasure("CAGR Matricula Macrosur", "CALCULATE (\n    [CAGR Matricula],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_ubicacion[es_macrosur] = TRUE\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR de la matricula de programas impartidos en la macrorregion sur en el rango de anios seleccionado.";

m = tabla.AddMeasure("CAGR Matricula Nacional", "CALCULATE (\n    [CAGR Matricula],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion )\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR de la matricula del pais en el rango de anios seleccionado.";

m = tabla.AddMeasure("CAGR Ingresantes UCSP", "CALCULATE (\n    [CAGR Ingresantes],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_universidad[es_ucsp] = TRUE\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR de los ingresantes de la UCSP en el rango de anios seleccionado.";

m = tabla.AddMeasure("CAGR Ingresantes Macrosur", "CALCULATE (\n    [CAGR Ingresantes],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_ubicacion[es_macrosur] = TRUE\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR de los ingresantes de programas impartidos en la macrorregion sur en el rango de anios seleccionado.";

m = tabla.AddMeasure("CAGR Ingresantes Nacional", "CALCULATE (\n    [CAGR Ingresantes],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion )\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR de los ingresantes del pais en el rango de anios seleccionado.";

m = tabla.AddMeasure("Ingresantes UCSP", "CALCULATE (\n    [Ingresantes],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_universidad[es_ucsp] = TRUE\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0";
m.Description = "Serie de referencia: ingresantes de la UCSP. Ignora universidad y ubicacion; respeta periodo, programa y gestion.";

m = tabla.AddMeasure("Ingresantes Macrosur", "CALCULATE (\n    [Ingresantes],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_ubicacion[es_macrosur] = TRUE\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0";
m.Description = "Serie de referencia: ingresantes de programas impartidos en la macrorregion sur. Ignora universidad y ubicacion; respeta periodo, programa y gestion.";

m = tabla.AddMeasure("Ingresantes Nacional", "CALCULATE (\n    [Ingresantes],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion )\n)");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0";
m.Description = "Serie de referencia: ingresantes del pais. Ignora universidad y ubicacion; respeta periodo, programa y gestion.";

m = tabla.AddMeasure("Indice Ingresantes UCSP", "VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )\nVAR Serie = [Ingresantes UCSP]\nVAR Base =\n    CALCULATE (\n        [Ingresantes UCSP],\n        REMOVEFILTERS ( dim_periodo ),\n        dim_periodo[anio] = AnioBase\n    )\nRETURN\n    DIVIDE ( Serie, Base ) * 100");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0.0";
m.Description = "Ingresantes de la UCSP en base 100 del primer anio seleccionado.";

m = tabla.AddMeasure("Indice Ingresantes Macrosur", "VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )\nVAR Serie = [Ingresantes Macrosur]\nVAR Base =\n    CALCULATE (\n        [Ingresantes Macrosur],\n        REMOVEFILTERS ( dim_periodo ),\n        dim_periodo[anio] = AnioBase\n    )\nRETURN\n    DIVIDE ( Serie, Base ) * 100");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0.0";
m.Description = "Ingresantes de programas impartidos en la macrorregion sur en base 100 del primer anio seleccionado.";

m = tabla.AddMeasure("Indice Ingresantes Nacional", "VAR AnioBase = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )\nVAR Serie = [Ingresantes Nacional]\nVAR Base =\n    CALCULATE (\n        [Ingresantes Nacional],\n        REMOVEFILTERS ( dim_periodo ),\n        dim_periodo[anio] = AnioBase\n    )\nRETURN\n    DIVIDE ( Serie, Base ) * 100");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "#,0.0";
m.Description = "Ingresantes del pais en base 100 del primer anio seleccionado.";

m = tabla.AddMeasure("Cuota de Mercado en el Sur", "DIVIDE ( [Matriculados], [Matricula Macrosur] )");
m.DisplayFolder = "06 Benchmark";
m.FormatString = "0.00%";
m.Description = "Porcentaje de la matricula de la macrorregion sur que capta la seleccion actual.";

m = tabla.AddMeasure("Tasa de Admision", "DIVIDE ( [Admitidos], [Postulaciones] )");
m.DisplayFolder = "07 Selectividad";
m.FormatString = "0.0%";
m.Description = "Admitidos sobre postulaciones. Mas bajo = mas selectivo. Ambos valores salen del mismo dataset de postulantes, asi que no depende de cruzar fuentes.";

m = tabla.AddMeasure("Tasa de Admision UCSP", "CALCULATE (\n    [Tasa de Admision],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_universidad[es_ucsp] = TRUE\n)");
m.DisplayFolder = "07 Selectividad";
m.FormatString = "0.0%";
m.Description = "Tasa de admision de la UCSP. Ignora universidad y ubicacion, respeta periodo, programa y gestion: en una tabla por campo de estudio da la del campo.";

m = tabla.AddMeasure("Tasa de Admision Resto del Sur", "-- Excluye a la UCSP por la misma razon que el benchmark de la 4.3: si no,\n-- la universidad se compararia contra un promedio que la contiene.\nCALCULATE (\n    [Tasa de Admision],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    REMOVEFILTERS ( dim_ubicacion ),\n    dim_ubicacion[es_macrosur] = TRUE,\n    dim_universidad[es_ucsp] = FALSE\n)");
m.DisplayFolder = "07 Selectividad";
m.FormatString = "0.0%";
m.Description = "Tasa de admision de los programas impartidos en la macrorregion sur por las DEMAS universidades. Es el comparador de la pregunta 4.4: en una tabla por campo de estudio, cada fila compara a la UCSP con sus equivalentes. Leer con el filtro de gestion en Privado: las publicas admiten 13-15 % y arrastran el promedio.";

m = tabla.AddMeasure("Tasa de Admision Privadas del Sur", "CALCULATE (\n    [Tasa de Admision Resto del Sur],\n    dim_universidad[tipo_gestion] = \"Privado\"\n)");
m.DisplayFolder = "07 Selectividad";
m.FormatString = "0.0%";
m.Description = "Tasa de admision de las DEMAS universidades privadas en la macrorregion sur. Es el comparador justo de la UCSP, que es privada: fija la gestion en vez de depender de que el usuario la filtre.";

m = tabla.AddMeasure("Tasa de Admision Publicas del Sur", "CALCULATE (\n    [Tasa de Admision Resto del Sur],\n    dim_universidad[tipo_gestion] = \"Público\"\n)");
m.DisplayFolder = "07 Selectividad";
m.FormatString = "0.0%";
m.Description = "Tasa de admision de las universidades publicas de la macrorregion sur. Se muestra como contexto: admiten entre 13 % y 15 % y arrastran cualquier promedio que las incluya.";

m = tabla.AddMeasure("HHI Universidad", "-- Ultimo anio en contexto, como los demas indicadores de stock: el HHI de un\n-- rango no es el promedio de sus HHI. Medido: con la UCSP y 2021-2025, el\n-- promedio daba 1 308; el valor de 2025 es 1 212.\nVAR UltimoAnio = MAX ( fct_concentracion[anio] )\nRETURN\n    CALCULATE ( AVERAGE ( fct_concentracion[hhi] ), dim_periodo[anio] = UltimoAnio )");
m.DisplayFolder = "08 Concentracion";
m.FormatString = "#,0";
m.Description = "Indice Herfindahl-Hirschman de la matricula entre programas de la universidad, escala 0-10000, en el ULTIMO anio del contexto. Alto = matricula concentrada en pocos programas. Precalculado en fct_concentracion.";

m = tabla.AddMeasure("HHI Mediana Macrosur", "-- La iteracion quita los filtros de universidad (salvo la gestion). Sin eso,\n-- un filtro de la UCSP llegaba hasta el CALCULATE interno, las demas\n-- universidades del sur quedaban sin valor y la mediana salia en blanco.\nVAR UltimoAnio = MAX ( fct_concentracion[anio] )\nVAR Universidades =\n    CALCULATETABLE (\n        VALUES ( fct_concentracion[codigo_inei] ),\n        ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n        dim_universidad[es_macrosur_sede] = TRUE,\n        dim_periodo[anio] = UltimoAnio\n    )\nRETURN\n    MEDIANX (\n        Universidades,\n        CALCULATE (\n            AVERAGE ( fct_concentracion[hhi] ),\n            ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n            dim_periodo[anio] = UltimoAnio\n        )\n    )");
m.DisplayFolder = "08 Concentracion";
m.FormatString = "#,0";
m.Description = "Mediana del HHI de las universidades con SEDE PRINCIPAL en la macrorregion sur en el ultimo anio del contexto, como referencia para juzgar si la UCSP esta mas o menos concentrada que sus pares. Filtra por dim_universidad[es_macrosur_sede]: fct_concentracion esta a grano anio x universidad y no se relaciona con dim_ubicacion.";

m = tabla.AddMeasure("CAGR OLS Ingresantes", "SELECTEDVALUE ( dim_tendencia_programa[cagr_ing] )");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "Crecimiento anual compuesto de los ingresantes del programa, estimado por regresion OLS sobre log(ingresantes) 2021-2025. A diferencia de [CAGR Ingresantes], que solo mira el primer y el ultimo anio, usa los cinco puntos.";

m = tabla.AddMeasure("CAGR OLS Matricula", "SELECTEDVALUE ( dim_tendencia_programa[cagr_mat] )");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "Crecimiento anual compuesto de la matricula del programa por regresion OLS sobre log(matriculados) 2021-2025. En un programa nuevo sube por acumulacion de cohortes aunque el ingreso caiga: leer siempre junto a [CAGR OLS Ingresantes].";

m = tabla.AddMeasure("CAGR Campo Sur Ingresantes", "SELECTEDVALUE ( dim_tendencia_programa[cagr_campo_sur_ing] )");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR OLS de los ingresantes del mismo campo CINE en la macrorregion sur, sin la UCSP. Es el benchmark sectorial de la pregunta 4.3.";

m = tabla.AddMeasure("CAGR Campo Sur Matricula", "SELECTEDVALUE ( dim_tendencia_programa[cagr_campo_sur_mat] )");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR OLS de la matricula del mismo campo CINE en la macrorregion sur, sin la UCSP.";

m = tabla.AddMeasure("Delta Ingresantes vs Campo Sur", "SELECTEDVALUE ( dim_tendencia_programa[delta_campo_sur_ing] )");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR OLS de ingresantes del programa menos el de su campo en el sur. Positivo = gana cuota de ingreso frente a sus equivalentes regionales.";

m = tabla.AddMeasure("Delta Matricula vs Campo Sur", "SELECTEDVALUE ( dim_tendencia_programa[delta_campo_sur_mat] )");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "+0.0%;-0.0%;0.0%";
m.Description = "CAGR OLS de matricula del programa menos el de su campo en el sur.";

m = tabla.AddMeasure("Programas Evaluados", "COALESCE (\n    CALCULATE (\n        DISTINCTCOUNT ( fct_matricula[programa_sk] ),\n        dim_tendencia_programa[lectura] <> \"Serie insuficiente\"\n    ),\n    0\n)");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "#,0";
m.Description = "Programas con serie suficiente para la regresion (4 anios o mas con dato). Es el denominador de las tres tarjetas de lectura.";

m = tabla.AddMeasure("Programas Crecimiento Confirmado", "-- Cuenta en el hecho y no en dim_tendencia_programa: asi respeta los\n-- segmentadores de universidad, gestion y ubicacion, que llegan a\n-- fct_matricula pero no a la dimension. El filtro sobre la lectura viaja de\n-- dim_tendencia_programa a dim_programa por la relacion 1:1 (bidireccional\n-- por definicion) y de ahi al hecho.\n-- COALESCE: es una medida de tarjeta. Cero programas es una respuesta, no un\n-- dato faltante, y una tarjeta en blanco se lee como lo segundo.\nCOALESCE (\n    CALCULATE (\n        DISTINCTCOUNT ( fct_matricula[programa_sk] ),\n        dim_tendencia_programa[lectura] = \"Crecimiento confirmado\"\n    ),\n    0\n)");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "#,0";
m.Description = "Programas con crecimiento sostenido en ingresantes Y en matricula: en las dos series, >= 4 anios con dato, p < 0,05 y CAGR >= 3 %.";

m = tabla.AddMeasure("Programas Caida Confirmada", "COALESCE (\n    CALCULATE (\n        DISTINCTCOUNT ( fct_matricula[programa_sk] ),\n        dim_tendencia_programa[lectura] = \"Caida confirmada\"\n    ),\n    0\n)");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "#,0";
m.Description = "Programas con caida sostenida en ingresantes Y en matricula.";

m = tabla.AddMeasure("Programas en Alerta", "COALESCE (\n    CALCULATE (\n        DISTINCTCOUNT ( fct_matricula[programa_sk] ),\n        dim_tendencia_programa[lectura] = \"Alerta: cae el ingreso\"\n    ),\n    0\n)");
m.DisplayFolder = "09 Tendencia";
m.FormatString = "#,0";
m.Description = "Programas cuyo ingreso cae de forma sostenida mientras la matricula aun no lo refleja: el indicador adelantado ya giro y el rezagado todavia no.";

m = tabla.AddMeasure("Matriculados Semestre", "-- La contraparte de [Matriculados]. Aqui el SUM directo es lo correcto\n-- PORQUE el semestre forma parte del contexto del visual: si el eje es el\n-- semestre, cada punto es un semestre y no hay doble conteo.\nSUM ( fct_matricula[matriculados] )");
m.DisplayFolder = "10 Semestral";
m.FormatString = "#,0";
m.Description = "Matriculados del semestre en contexto. Es la medida fiel al grano del hecho: respeta el slicer de semestre y no impone ninguno. Usar solo en visuales que tengan el semestre en el eje o en el filtro.";

m = tabla.AddMeasure("Retencion Intra-anual", "-- Este indicador era imposible antes de ampliar la ingesta: con un solo\n-- semestre descargado por anio no habia con que comparar. Ahora sale de dos\n-- CALCULATE sobre el mismo hecho.\nVAR Primero = CALCULATE (\n        SUM ( fct_matricula[matriculados] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[semestre] = 1\n    )\nVAR Segundo = CALCULATE (\n        SUM ( fct_matricula[matriculados] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[semestre] = 2\n    )\nRETURN\n    DIVIDE ( Segundo, Primero )");
m.DisplayFolder = "10 Semestral";
m.FormatString = "0.0%";
m.Description = "Matriculados del semestre II sobre los del semestre I del mismo anio. Por debajo de 100% hay perdida de matricula dentro del anio. No es desercion exacta: no sigue a las mismas personas, compara volumenes.";

m = tabla.AddMeasure("Egresados", "-- Aqui SI se suman los dos semestres, y es correcto: egresar es un\n-- FLUJO (ocurre una vez), mientras matricularse es un STOCK (se repite cada\n-- semestre). Por eso [Matriculados] fija el semestre y esta medida no.\n-- Es la distincion que decide si un SUM sobre un hecho semestral esta bien.\nSUM ( fct_egresados[egresados] )");
m.DisplayFolder = "11 Egresados";
m.FormatString = "#,0";
m.Description = "Personas distintas que egresan (terminan los cursos) del programa en el anio. OJO: el slicer de departamento no afecta a esta medida, porque la fuente de egresados no publica la geografia del local de egreso.";

m = tabla.AddMeasure("Nota Promedio al Egreso", "-- Ponderado, no un AVERAGE de los promedios: fct_egresados ya trae una\n-- nota PROMEDIO por fila, y promediar promedios de grupos de tamano distinto\n-- da un numero que no corresponde a ningun alumno. Se repondera por egresados.\nDIVIDE (\n    SUMX ( fct_egresados, fct_egresados[nota_promedio] * fct_egresados[egresados] ),\n    SUM ( fct_egresados[egresados] )\n)");
m.DisplayFolder = "11 Egresados";
m.FormatString = "0.00";
m.Description = "Nota promedio ponderada por numero de egresados. Unica medida de desempeno academico disponible en el portal.";

m = tabla.AddMeasure("Personas Tituladas", "SUM ( fct_titulos[personas] )");
m.DisplayFolder = "11 Egresados";
m.FormatString = "#,0";
m.Description = "Personas distintas que obtuvieron un grado o titulo en el anio. Es la cifra comparable con un conteo de egresados. Solo valido a grano universidad.";

m = tabla.AddMeasure("Titulados por Egresado", "-- POR QUE ESTA MEDIDA NO SE LLAMA \"Tasa de Titulacion\", que era su primer\n-- nombre. Una tasa exige que numerador y denominador describan a la MISMA\n-- gente, y aqui no lo hacen por dos motivos que se midieron:\n--\n--   1. Doble conteo. SUM(fct_titulos[titulos]) cuenta EVENTOS: 437 872\n--      personas tienen el grado de bachiller Y el titulo profesional, asi que\n--      el numerador salia al doble. Se usa [Personas Tituladas], que cuenta\n--      personas distintas.\n--\n--   2. Cohortes distintas. Los titulos se confieren con anos de rezago\n--      respecto al egreso. Medido en la UCSP para 2024: 876 grados de\n--      bachiller contra 755 egresados -- mas bachilleres que egresados del\n--      ano, porque los grados corresponden a quienes egresaron antes.\n--\n-- Con el nombre anterior la medida reportaba un 206 % y nadie podia saber si\n-- era un dato o un error. El nombre nuevo describe exactamente la division que\n-- hace, y la limitacion vive en la descripcion, que es lo que Power BI muestra\n-- al pasar el cursor.\n--\n-- GUARDA DE GRANO, por el mismo motivo que [Ratio Alumno Docente]:\n-- fct_titulos no se relaciona con dim_programa ni con dim_ubicacion.\n-- Y sobre el UNIVERSO COMUN, igual que [Ratio Alumno Docente]: solo\n-- universidades que reportan titulos y egresados.\nVAR FiltroFino = ISFILTERED ( dim_programa ) || ISFILTERED ( dim_ubicacion )\nVAR Comunes =\n    FILTER (\n        VALUES ( dim_universidad[codigo_inei] ),\n        NOT ISBLANK ( [Personas Tituladas] ) && NOT ISBLANK ( [Egresados] )\n    )\nRETURN\n    IF (\n        FiltroFino,\n        BLANK (),\n        DIVIDE ( SUMX ( Comunes, [Personas Tituladas] ), SUMX ( Comunes, [Egresados] ) )\n    )");
m.DisplayFolder = "11 Egresados";
m.FormatString = "0.00";
m.Description = "Personas tituladas en el anio divididas por los egresados del MISMO anio. NO es una tasa de titulacion: compara dos flujos con rezagos distintos, porque quien se titula en 2024 egreso varios anios antes. Por encima de 1 significa que se titula mas gente de la que egresa ese anio, lo que pasa cuando la institucion reduce un rezago acumulado. Se anula si hay filtro de programa o de ubicacion. Se calcula sobre el universo comun: solo universidades que reportan las dos fuentes (control de calidad #17).";

m = tabla.AddMeasure("Egresados por Ingresante", "-- La limitacion esta en la descripcion a proposito: la medida es util y\n-- barata, pero leerla como \"tasa de graduacion\" seria un error. Un indicador\n-- de cohorte exigiria seguir a las mismas personas, y GUID_PERSONA no permite\n-- hacerlo entre datasets distintos del portal.\n--\n-- GUARDA DE GRANO: fct_egresados no se relaciona con dim_ubicacion. Con un\n-- filtro geografico [Ingresantes] se filtraria y [Egresados] no, y el cociente\n-- compararia todo el pais contra un departamento.\n-- Y sobre el UNIVERSO COMUN: 17 a 43 universidades con ingresantes no\n-- reportan egresados segun el anio (control #17), y bajarian el cociente.\nVAR Comunes =\n    FILTER (\n        VALUES ( dim_universidad[codigo_inei] ),\n        NOT ISBLANK ( [Egresados] ) && NOT ISBLANK ( [Ingresantes] )\n    )\nRETURN\n    IF (\n        ISFILTERED ( dim_ubicacion ),\n        BLANK (),\n        DIVIDE ( SUMX ( Comunes, [Egresados] ), SUMX ( Comunes, [Ingresantes] ) )\n    )");
m.DisplayFolder = "11 Egresados";
m.FormatString = "0.00";
m.Description = "Egresados del anio sobre ingresantes del mismo anio. NO es una tasa de graduacion: compara dos cohortes distintas, porque quien egresa en 2025 ingreso cinco anios antes. Sirve para ver si la salida y la entrada estan en equilibrio, no para medir exito individual. Se calcula sobre el universo comun: solo universidades que reportan las dos fuentes (control de calidad #17).";

m = tabla.AddMeasure("Docentes", "-- Mismo tratamiento que [Matriculados], en los dos ejes: el plantel es un\n-- STOCK. Sumar semestres contaria dos veces al mismo profesor, y sumar anios\n-- hasta cinco veces.\nVAR UltimoAnio =\n    CALCULATE (\n        MAX ( fct_docentes[anio] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[es_serie_anual] = TRUE\n    )\nRETURN\n    CALCULATE (\n        SUM ( fct_docentes[docentes] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[es_serie_anual] = TRUE,\n        dim_periodo[anio] = UltimoAnio\n    )");
m.DisplayFolder = "12 Docentes";
m.FormatString = "#,0";
m.Description = "Docentes distintos de pregrado en la serie anual comparable. La fuente repite al docente por cada grado que acredita; el hecho ya cuenta personas distintas.";

m = tabla.AddMeasure("% Docentes Tiempo Completo", "-- Numerador al mismo grano que [Docentes]: serie anual y ultimo anio en\n-- contexto. Si no, con varios anios el cociente mezclaria granos.\nVAR UltimoAnio =\n    CALCULATE (\n        MAX ( fct_docentes[anio] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[es_serie_anual] = TRUE\n    )\nVAR Completo =\n    CALCULATE (\n        SUM ( fct_docentes[docentes_tiempo_completo] ),\n        REMOVEFILTERS ( dim_semestre ),\n        dim_semestre[es_serie_anual] = TRUE,\n        dim_periodo[anio] = UltimoAnio\n    )\nRETURN\n    DIVIDE ( Completo, [Docentes] )");
m.DisplayFolder = "12 Docentes";
m.FormatString = "0.0%";
m.Description = "Docentes a tiempo completo o dedicacion exclusiva sobre el total. Condicion Basica de Calidad del licenciamiento SUNEDU.";

m = tabla.AddMeasure("Ratio Alumno Docente", "-- GUARDA DE GRANO, la misma de [Titulados por Egresado] y por el mismo\n-- motivo. Es el error mas facil de cometer con este modelo: filtrar un\n-- programa haria caer el numerador a la matricula de ese programa mientras el\n-- denominador sigue siendo TODO el plantel de la universidad, y el ratio\n-- pareceria de 3 alumnos por docente. Devolver BLANK es la respuesta honesta.\n-- La guarda mira las TABLAS, no columnas sueltas: asi cubre cualquier campo\n-- de programa o de ubicacion, incluida la macrorregion, que es un filtro\n-- obligatorio del enunciado y tampoco llega a fct_docentes.\n-- UNIVERSO COMUN: numerador y denominador se suman solo sobre las\n-- universidades que reportan LAS DOS fuentes. Un cociente directo mezcla dos\n-- universos: medido en 2025, el ratio alumno/docente del pais da 20,9 directo y\n-- 19,5 sobre el universo comun, porque hay universidades con matricula y sin\n-- docentes reportados. Es el mismo error que producia el 206 % de titulacion\n-- (control de calidad #17).\n-- Y en UN solo anio, el ultimo del contexto: sin fijarlo, con un rango de\n-- anios cada universidad aportaba su propio ultimo anio y el ratio mezclaba\n-- fechas (medido: 15,27 contra 15,40 de 2025 en el sur).\nVAR FiltroFino = ISFILTERED ( dim_programa ) || ISFILTERED ( dim_ubicacion )\nVAR UltimoAnio = MAX ( fct_docentes[anio] )\nVAR Ratio =\n    CALCULATE (\n        VAR Comunes =\n            FILTER (\n                VALUES ( dim_universidad[codigo_inei] ),\n                NOT ISBLANK ( [Docentes] ) && NOT ISBLANK ( [Matriculados] )\n            )\n        RETURN\n            DIVIDE ( SUMX ( Comunes, [Matriculados] ), SUMX ( Comunes, [Docentes] ) ),\n        dim_periodo[anio] = UltimoAnio\n    )\nRETURN\n    IF ( FiltroFino, BLANK (), Ratio )");
m.DisplayFolder = "12 Docentes";
m.FormatString = "0.0";
m.Description = "Matriculados por cada docente, sobre las universidades que reportan las dos fuentes. Se anula si hay filtro de programa o de ubicacion: la fuente de docentes no trae programa ni local, asi que a ese grano el ratio compararia cosas distintas.";

m = tabla.AddMeasure("Ratio Alumno Docente Macrosur", "-- Se filtra por dim_universidad[es_macrosur_sede] y no por dim_ubicacion,\n-- porque fct_docentes no se relaciona con dim_ubicacion. La definicion de\n-- universidad del sur es la declarada en dim_universidad: aquella cuya sede\n-- principal, por volumen de matricula, esta en la macrorregion sur.\n-- Llama a [Ratio Alumno Docente] para heredar su guarda de grano.\nCALCULATE (\n    [Ratio Alumno Docente],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] ),\n    dim_universidad[es_macrosur_sede] = TRUE\n)");
m.DisplayFolder = "12 Docentes";
m.FormatString = "0.0";
m.Description = "Ratio alumno/docente del conjunto de universidades con sede en la macrorregion sur, para comparar contra la UCSP.";

m = tabla.AddMeasure("Ratio Alumno Docente Nacional", "-- Llama a [Ratio Alumno Docente] para heredar su guarda de grano.\nCALCULATE (\n    [Ratio Alumno Docente],\n    ALLEXCEPT ( dim_universidad, dim_universidad[tipo_gestion] )\n)");
m.DisplayFolder = "12 Docentes";
m.FormatString = "0.0";
m.Description = "Ratio alumno/docente del sistema universitario completo.";

m = tabla.AddMeasure("Rango de Anios", "VAR Desde = MINX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )\nVAR Hasta = MAXX ( ALLSELECTED ( dim_periodo[anio] ), dim_periodo[anio] )\nRETURN\n    IF ( Desde = Hasta, FORMAT ( Desde, \"0\" ), FORMAT ( Desde, \"0\" ) & \"-\" & FORMAT ( Hasta, \"0\" ) )");
m.DisplayFolder = "13 Narrativa";
m.FormatString = "";
m.Description = "Rango de anios seleccionado, para los titulos de los visuales.";

m = tabla.AddMeasure("Titular Resumen", "VAR MatU = [CAGR Matricula UCSP]\nVAR IngU = [CAGR Ingresantes UCSP]\nVAR IngS = [CAGR Ingresantes Macrosur]\nRETURN\n    IF (\n        NOT ISBLANK ( MatU ) && NOT ISBLANK ( IngU ),\n        \"En \" & [Rango de Anios] & \", la matrícula de la UCSP \"\n            & IF ( MatU >= 0, \"crece \", \"cae \" ) & FORMAT ( ABS ( MatU ), \"0.0%\" )\n            & \" al año y su ingreso \"\n            & IF ( IngU >= 0, \"crece \", \"cae \" ) & FORMAT ( ABS ( IngU ), \"0.0%\" )\n            & \"; el ingreso del sur \"\n            & IF ( IngS >= 0, \"crece \", \"cae \" ) & FORMAT ( ABS ( IngS ), \"0.0%\" ) & \".\"\n    )");
m.DisplayFolder = "13 Narrativa";
m.FormatString = "";
m.Description = "Frase de cabecera del resumen ejecutivo y de la pagina 4.1.";

m = tabla.AddMeasure("Titular Demanda", "VAR Programas =\n    FILTER (\n        ADDCOLUMNS ( ALLSELECTED ( dim_programa[nombre_programa] ), \"@v\", [Ingresantes] ),\n        [@v] >= 10\n    )\nVAR Mayor = TOPN ( 1, Programas, [@v], DESC )\nVAR Menor = TOPN ( 1, Programas, [@v], ASC )\nRETURN\n    IF (\n        NOT ISEMPTY ( Programas ),\n        \"Mayor ingreso: \" & MAXX ( Mayor, dim_programa[nombre_programa] )\n            & \" (\" & FORMAT ( MAXX ( Mayor, [@v] ), \"#,0\" ) & \"). Menor: \"\n            & MAXX ( Menor, dim_programa[nombre_programa] )\n            & \" (\" & FORMAT ( MAXX ( Menor, [@v] ), \"#,0\" ) & \").\"\n    )");
m.DisplayFolder = "13 Narrativa";
m.FormatString = "";
m.Description = "Frase de cabecera de la pagina 4.2: el programa de mayor y de menor ingreso dentro de los filtros activos.";

m = tabla.AddMeasure("Titular Tendencia", "VAR Conf = [Programas Crecimiento Confirmado]\nVAR Caida = [Programas Caida Confirmada]\nVAR Alerta = [Programas en Alerta]\nVAR TxtConf =\n    IF (\n        Conf = 0,\n        \"Ningún programa crece\",\n        FORMAT ( Conf, \"0\" ) & IF ( Conf = 1, \" programa crece\", \" programas crecen\" )\n    ) & \" en ingreso y matrícula a la vez\"\nVAR TxtCaida = FORMAT ( Caida, \"0\" ) & IF ( Caida = 1, \" cae\", \" caen\" ) & \" en las dos series\"\nVAR TxtAlerta =\n    FORMAT ( Alerta, \"0\" ) & IF ( Alerta = 1, \" ya pierde\", \" ya pierden\" )\n        & \" ingreso sin que la matrícula lo refleje\"\nRETURN\n    CONCATENATE ( TxtConf & \"; \" & TxtCaida & \" y \" & TxtAlerta, \".\" )");
m.DisplayFolder = "13 Narrativa";
m.FormatString = "";
m.Description = "Frase de cabecera de la pagina 4.3, con singular y plural resueltos.";

m = tabla.AddMeasure("Titular Selectividad", "VAR U = [Tasa de Admision UCSP]\nVAR P = [Tasa de Admision Privadas del Sur]\nRETURN\n    IF (\n        NOT ISBLANK ( U ) && NOT ISBLANK ( P ),\n        \"La UCSP admite el \" & FORMAT ( U, \"0%\" ) & \" de sus postulaciones; las demás privadas del sur, el \"\n            & FORMAT ( P, \"0%\" ) & \". \"\n            & IF (\n                ABS ( U - P ) < 0.03,\n                \"Su selectividad es similar a la de sus pares.\",\n                IF ( U < P, \"Es más selectiva que sus pares.\", \"Es menos selectiva que sus pares.\" )\n            )\n    )");
m.DisplayFolder = "13 Narrativa";
m.FormatString = "";
m.Description = "Frase de cabecera de la pagina 4.4: la UCSP frente a sus pares privados. Una diferencia menor a 3 puntos se lee como similar: no se afirma mas de lo que el dato sostiene.";


Info("79 medidas creadas.");
