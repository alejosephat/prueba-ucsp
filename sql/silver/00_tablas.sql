-- Capa SILVER: esquema unificado para las tres fuentes.
-- Las columnas divergentes entre ingresante y matriculado (PROCESO_ESTANDARIZADO
-- vs PERIODO_ESTANDARIZADO, CODIGO_SIU_FILIAL vs CODIGO_LOCAL, DEPARTAMENTO_FILIAL
-- vs DEPARTAMENTO_LOCAL, LICENCIADO vs LICENCIA) se unifican aqui.

-- QUE CUENTA COMO ESPACIO EN BLANCO. No es una pregunta retorica: la fuente
-- usa, ademas del espacio normal, tabuladores y el ESPACIO DURO chr(160), que
-- se ve igual que un espacio pero es otro caracter.
--
-- Y los dos valores por defecto de DuckDB se quedan cortos:
--   trim(s)  quita SOLO espacios, no tabuladores ni chr(160).
--   El \s de su motor de regex (RE2) cubre [\t\n\f\r ] pero NO chr(160).
--
-- Esto no es teorico. Se descubrio al contrastar las UDF del notebook de
-- Fabric contra estas macros sobre los 8 765 valores distintos de texto de
-- silver: salieron 4 diferencias, y las macros eran las que estaban mal.
-- silver_titulo.nombre_entidad trae 588 filas con un espacio duro dentro del
-- nombre, y sin este tratamiento ese nombre no puede casar con dim_universidad
-- aunque sea el mismo. De ahi que los caracteres se nombren explicitamente.
CREATE OR REPLACE MACRO blancos() AS chr(9) || chr(10) || chr(12) || chr(13) || ' ' || chr(160);

-- Deja el texto tal como lo publica SUNEDU (para mostrar en el dashboard),
-- pero con el espacio duro convertido en espacio normal, los blancos de los
-- extremos recortados y los nulos de la fuente ('<NULL>' y cadena vacia)
-- convertidos en NULL real.
CREATE OR REPLACE MACRO limpio(s) AS
    nullif(nullif(trim(replace(s, chr(160), ' '), blancos()), '<NULL>'), '');

-- Normaliza para usar como llave: lo de limpio(), mas quitar tildes, pasar a
-- mayusculas y colapsar espacios interiores.
-- Reusa limpio() a proposito: las dos funciones tienen que tratar los blancos
-- igual, y con una sola definicion no pueden divergir.
CREATE OR REPLACE MACRO norm(s) AS
    nullif(upper(trim(regexp_replace(strip_accents(limpio(s)), '\s+', ' ', 'g'),
                      blancos())), '');

DROP TABLE IF EXISTS silver_ingresante;
CREATE TABLE silver_ingresante (
    anio                SMALLINT,
    codigo_inei         VARCHAR,
    nombre_entidad      VARCHAR,
    tipo_entidad        VARCHAR,
    tipo_gestion        VARCHAR,
    tipo_constitucion   VARCHAR,
    licenciamiento      VARCHAR,
    nivel_academico     VARCHAR,
    codigo_siu_programa VARCHAR,
    codigo_grupo_1      VARCHAR,
    nombre_grupo_1      VARCHAR,
    codigo_grupo_3      VARCHAR,
    nombre_grupo_3      VARCHAR,
    nombre_programa     VARCHAR,
    departamento        VARCHAR,
    provincia           VARCHAR,
    guid_persona        VARCHAR,
    sexo                VARCHAR,
    edad                SMALLINT
);

DROP TABLE IF EXISTS silver_matriculado;
CREATE TABLE silver_matriculado (
    anio                SMALLINT,
    semestre            TINYINT,
    codigo_inei         VARCHAR,
    nombre_entidad      VARCHAR,
    tipo_entidad        VARCHAR,
    tipo_gestion        VARCHAR,
    tipo_constitucion   VARCHAR,
    licenciamiento      VARCHAR,
    nivel_academico     VARCHAR,
    codigo_siu_programa VARCHAR,
    codigo_grupo_1      VARCHAR,
    nombre_grupo_1      VARCHAR,
    codigo_grupo_3      VARCHAR,
    nombre_grupo_3      VARCHAR,
    nombre_programa     VARCHAR,
    departamento        VARCHAR,
    provincia           VARCHAR,
    guid_persona        VARCHAR,
    sexo                VARCHAR,
    edad                SMALLINT,
    anio_ingreso        SMALLINT
);

-- Registro de filas leidas por archivo crudo: insumo del control de calidad #1
-- (conciliacion bronze -> gold). Se llena en la capa bronze, antes de filtrar.
DROP TABLE IF EXISTS silver_conteo_crudo;
CREATE TABLE silver_conteo_crudo (
    fuente        VARCHAR,
    periodo       VARCHAR,
    filas_crudas  BIGINT,
    filas_pregrado BIGINT
);

-- Postulantes. Grano del crudo: una fila por postulacion (persona-proceso).
-- El crudo trae hasta 3 opciones de programa; se usa la PRIMERA OPCION, que es
-- la que expresa la demanda real por el programa y la que pareja con ingresantes.
-- ES_INGRESANTE viene en la propia fuente -> la selectividad se calcula dentro
-- de la misma tabla, sin cruzar datasets ni asumir rezagos.
DROP TABLE IF EXISTS silver_postulante;
CREATE TABLE silver_postulante (
    anio                SMALLINT,
    codigo_inei         VARCHAR,
    nombre_entidad      VARCHAR,
    tipo_entidad        VARCHAR,
    tipo_gestion        VARCHAR,
    tipo_constitucion   VARCHAR,
    licenciamiento      VARCHAR,
    nivel_academico     VARCHAR,
    modalidad_ingreso   VARCHAR,
    codigo_siu_programa VARCHAR,
    codigo_grupo_1      VARCHAR,
    nombre_grupo_1      VARCHAR,
    codigo_grupo_3      VARCHAR,
    nombre_grupo_3      VARCHAR,
    nombre_programa     VARCHAR,
    departamento        VARCHAR,
    provincia           VARCHAR,
    guid_persona        VARCHAR,
    sexo                VARCHAR,
    edad                SMALLINT,
    es_ingresante       BOOLEAN
);

-- ---------------------------------------------------------------------------
-- Datasets incorporados al ampliar la ingesta al catalogo completo de TUNI.
-- Cada uno trae su propio problema de integracion; esta declarado arriba de
-- la tabla porque es lo que decide si llega o no a gold.
-- ---------------------------------------------------------------------------

-- Egresados. Grano del crudo: una fila por persona que egresa.
-- Integra limpio: trae codigo_inei Y codigo_siu_programa, las dos llaves del
-- modelo. PERIODO_EGRESO viene como '2025-1', igual que la matricula, asi que
-- se parte en anio y semestre.
-- Aporta dos medidas que ninguna otra fuente tiene: creditos y nota promedio.
DROP TABLE IF EXISTS silver_egresado;
CREATE TABLE silver_egresado (
    anio                SMALLINT,
    semestre            TINYINT,
    codigo_inei         VARCHAR,
    nombre_entidad      VARCHAR,
    tipo_entidad        VARCHAR,
    tipo_gestion        VARCHAR,
    tipo_constitucion   VARCHAR,
    licenciamiento      VARCHAR,
    nivel_academico     VARCHAR,
    codigo_siu_programa VARCHAR,
    codigo_grupo_1      VARCHAR,
    nombre_grupo_1      VARCHAR,
    codigo_grupo_3      VARCHAR,
    nombre_grupo_3      VARCHAR,
    nombre_programa     VARCHAR,
    departamento        VARCHAR,
    provincia           VARCHAR,
    guid_persona        VARCHAR,
    sexo                VARCHAR,
    edad                SMALLINT,
    creditos_aprobados  DECIMAL(8, 3),
    nota_promedio       DECIMAL(5, 2)
);

-- Docentes. OJO CON EL GRANO: esta fuente NO trae codigo_siu_programa, y su
-- unica geografia es el departamento de NACIMIENTO del docente, no el del local
-- donde ensena. Por eso el hecho que sale de aqui vive a grano
-- universidad x semestre y NO se relaciona con dim_programa ni dim_ubicacion.
-- Eso no es un defecto del modelo: es un hecho a grano mas grueso, que en un
-- esquema estrella es legitimo mientras la granularidad este declarada.
-- Nombres divergentes respecto de las otras fuentes: ENTIDAD (no
-- NOMBRE_ENTIDAD), PERIODO_ESTANDAR (no PERIODO_ESTANDARIZADO), LICENCIA.
DROP TABLE IF EXISTS silver_docente;
CREATE TABLE silver_docente (
    anio                SMALLINT,
    semestre            TINYINT,
    codigo_inei         VARCHAR,
    nombre_entidad      VARCHAR,
    tipo_entidad        VARCHAR,
    tipo_gestion        VARCHAR,
    tipo_constitucion   VARCHAR,
    licenciamiento      VARCHAR,
    nivel_academico     VARCHAR,
    guid_persona        VARCHAR,
    tipo_grado_titulo   VARCHAR,
    condicion_laboral   VARCHAR,
    regimen_dedicacion  VARCHAR,
    sexo                VARCHAR,
    edad                SMALLINT
);

-- Carnes universitarios emitidos. Es un registro ADMINISTRATIVO: cuenta
-- tramites, no alumnos matriculados. Un alumno de 5 anios puede tener 1 carne
-- o ninguno. Por eso NO entra como hecho: se usa como contraste independiente
-- de la matricula (control de calidad #12). Y el contraste dio un hallazgo
-- sobre la fuente: su columna GUID no identifica personas, sino lotes de
-- emision por universidad (control #15). Por eso guid_persona se conserva con
-- ese nombre -- es el nombre del campo en el crudo -- pero ninguna medida
-- cuenta valores distintos sobre el.
-- Geografia: UBICACION viene como 'LIMA/LIMA/LIMA' -> se parte en tres.
DROP TABLE IF EXISTS silver_carne;
CREATE TABLE silver_carne (
    anio                SMALLINT,
    codigo_inei         VARCHAR,
    nombre_entidad      VARCHAR,
    nivel_academico     VARCHAR,
    codigo_siu_programa VARCHAR,
    nombre_programa     VARCHAR,
    departamento        VARCHAR,
    provincia           VARCHAR,
    guid_persona        VARCHAR
);

-- Grados y titulos nacionales. Mide titulacion EFECTIVA (obtener el diploma),
-- que no es lo mismo que egresar (terminar los cursos). La brecha entre ambos
-- es la tasa de titulacion, un indicador real de eficiencia institucional.
--
-- PROBLEMA DE INTEGRACION, y es el que decide su destino: esta fuente no trae
-- codigo_inei ni codigo_siu_programa. Trae CODIGO_ENTIDAD ('065'), que es otro
-- codigo distinto, y NOMBRE_CARRERA en texto libre. La unica llave posible es
-- el nombre de la universidad normalizado -- un match exacto sobre texto
-- normalizado, NO fuzzy matching. La tasa de match se mide en el control #11
-- y de ese numero depende si el hecho llega a gold o se declara excluido.
-- Trae FECHA_MATRICULA y FECHA_EGRESO -> permite medir duracion real de estudios.
DROP TABLE IF EXISTS silver_titulo;
CREATE TABLE silver_titulo (
    anio                SMALLINT,
    nombre_entidad      VARCHAR,
    tipo_entidad        VARCHAR,
    tipo_gestion        VARCHAR,
    licenciamiento      VARCHAR,
    nivel_academico     VARCHAR,
    departamento_sede   VARCHAR,
    nombre_carrera      VARCHAR,
    abreviatura_grado   VARCHAR,
    modalidad_obtencion VARCHAR,
    anios_estudio       DECIMAL(5, 2),
    guid_persona        VARCHAR,
    sexo                VARCHAR
);
