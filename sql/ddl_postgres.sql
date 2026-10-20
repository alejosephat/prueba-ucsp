-- Modelo estrella en PostgreSQL.
-- La logica de transformacion (sql/silver/ y sql/gold/) corre sin cambios sobre
-- este esquema: solo cambia la capa de ingesta (sql/bronze/), que en el entorno
-- institucional no leeria CSV sino las tablas del SIS/ERP.

CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE gold.dim_periodo (
    anio            SMALLINT     PRIMARY KEY,
    etiqueta        VARCHAR(4)   NOT NULL,
    orden           SMALLINT     NOT NULL,
    es_ultimo_anio  BOOLEAN      NOT NULL,
    es_tendencia    BOOLEAN         NOT NULL   -- anio incluido en la regresion de tendencia (2020 queda fuera)
);

-- Grano: periodo lectivo. La fila 0 = 'Otro' recoge los periodos de egreso
-- extraordinarios (3, 4 y vacio) que trae la fuente de egresados; sin ella
-- esas filas quedarian huerfanas. Ver sql/gold/14_dim_semestre.sql.
CREATE TABLE gold.dim_semestre (
    semestre        SMALLINT    PRIMARY KEY,   -- 1, 2, o 0 = 'Otro'
    etiqueta        VARCHAR(4)  NOT NULL,
    es_serie_anual  BOOLEAN     NOT NULL       -- marca el semestre de la serie anual comparable
);

CREATE TABLE gold.dim_universidad (
    codigo_inei        VARCHAR(12)  PRIMARY KEY,
    nombre_universidad VARCHAR(255) NOT NULL,
    tipo_entidad       VARCHAR(50),
    tipo_gestion       VARCHAR(20),
    tipo_constitucion  VARCHAR(50),
    licenciamiento     VARCHAR(50),
    departamento_sede  VARCHAR(60),
    macrorregion_sede  VARCHAR(20),
    es_macrosur_sede   BOOLEAN      NOT NULL,
    es_ucsp            BOOLEAN      NOT NULL
);

-- codigo_inei es FK por integridad referencial en la base, pero en el modelo
-- semantico NO debe crearse esa relacion: abriria una segunda ruta de filtrado
-- hacia los hechos y Power BI la reportaria como ambigua.
CREATE TABLE gold.dim_programa (
    programa_sk         CHAR(32)     PRIMARY KEY,   -- md5(codigo_inei || '-' || codigo_siu_programa)
    codigo_inei         VARCHAR(12)  NOT NULL REFERENCES gold.dim_universidad,
    codigo_siu_programa VARCHAR(20)  NOT NULL,
    nombre_programa     VARCHAR(255),
    nombre_programa_std VARCHAR(255),
    codigo_grupo_1      VARCHAR(10),
    nombre_grupo_1      VARCHAR(120),               -- CINE-UNESCO, 11 campos amplios
    codigo_grupo_3      VARCHAR(10),
    nombre_grupo_3      VARCHAR(120),               -- CINE-UNESCO, 83 campos detallados
    campo_estudio       VARCHAR(120) NOT NULL,      -- nombre_grupo_3, o 'Sin clasificar CINE'
    nivel_academico     VARCHAR(50),
    CONSTRAINT uq_programa UNIQUE (codigo_inei, codigo_siu_programa)
);

CREATE TABLE gold.dim_ubicacion (
    ubicacion_sk  CHAR(32)     PRIMARY KEY,         -- md5(departamento || '-' || provincia)
    departamento  VARCHAR(60)  NOT NULL,
    provincia     VARCHAR(60),
    macrorregion  VARCHAR(20)  NOT NULL,
    es_macrosur   BOOLEAN      NOT NULL
);

-- Salida del componente estadistico (04_tendencias.py): una fila por programa,
-- con la regresion OLS sobre ingresantes (_ing) y sobre matricula (_mat).
CREATE TABLE gold.dim_tendencia_programa (
    programa_sk              CHAR(32) PRIMARY KEY REFERENCES gold.dim_programa,
    anios_ing                SMALLINT,
    cagr_ing                 NUMERIC(10, 6),
    p_valor_ing              NUMERIC(10, 6),
    tendencia_ing            VARCHAR(30),
    ingresantes_ultimo_anio  INTEGER,
    cagr_campo_sur_ing       NUMERIC(10, 6),
    delta_campo_sur_ing      NUMERIC(10, 6),
    cuadrante_ing            VARCHAR(40),
    anios_mat                SMALLINT,
    cagr_mat                 NUMERIC(10, 6),
    p_valor_mat              NUMERIC(10, 6),
    tendencia_mat            VARCHAR(30),
    matriculados_ultimo_anio INTEGER,
    cagr_campo_sur_mat       NUMERIC(10, 6),
    delta_campo_sur_mat      NUMERIC(10, 6),
    cuadrante_mat            VARCHAR(40),
    lectura                  VARCHAR(40)
);

-- GRANULARIDAD: una fila por anio x universidad x programa x ubicacion.
CREATE TABLE gold.fct_ingresantes (
    anio         SMALLINT    NOT NULL REFERENCES gold.dim_periodo,
    codigo_inei  VARCHAR(12) NOT NULL REFERENCES gold.dim_universidad,
    programa_sk  CHAR(32)    NOT NULL REFERENCES gold.dim_programa,
    ubicacion_sk CHAR(32)    NOT NULL REFERENCES gold.dim_ubicacion,
    ingresantes  INTEGER     NOT NULL,
    PRIMARY KEY (anio, programa_sk, ubicacion_sk)
);

-- GRANULARIDAD: una fila por anio x SEMESTRE x universidad x programa x ubicacion,
-- con el semestre como parte del grano: estan los 12 semestres de 2020-I a
-- 2025-II. La serie anual comparable se obtiene filtrando
-- dim_semestre.es_serie_anual, que es un filtro de consulta y no un recorte
-- de datos (ver 21_fct_matricula.sql).
CREATE TABLE gold.fct_matricula (
    anio         SMALLINT    NOT NULL REFERENCES gold.dim_periodo,
    semestre     SMALLINT    NOT NULL REFERENCES gold.dim_semestre,
    codigo_inei  VARCHAR(12) NOT NULL REFERENCES gold.dim_universidad,
    programa_sk  CHAR(32)    NOT NULL REFERENCES gold.dim_programa,
    ubicacion_sk CHAR(32)    NOT NULL REFERENCES gold.dim_ubicacion,
    matriculados INTEGER     NOT NULL,
    PRIMARY KEY (anio, semestre, programa_sk, ubicacion_sk)
);

-- GRANULARIDAD: una fila por anio x universidad x programa (1a opcion) x ubicacion.
CREATE TABLE gold.fct_postulantes (
    anio          SMALLINT    NOT NULL REFERENCES gold.dim_periodo,
    codigo_inei   VARCHAR(12) NOT NULL REFERENCES gold.dim_universidad,
    programa_sk   CHAR(32)    NOT NULL REFERENCES gold.dim_programa,
    ubicacion_sk  CHAR(32)    NOT NULL REFERENCES gold.dim_ubicacion,
    postulaciones INTEGER     NOT NULL,
    postulantes   INTEGER     NOT NULL,
    admitidos     INTEGER     NOT NULL,
    PRIMARY KEY (anio, programa_sk, ubicacion_sk)
);

-- GRANULARIDAD: una fila por anio x universidad.
CREATE TABLE gold.fct_concentracion (
    anio                     SMALLINT    NOT NULL REFERENCES gold.dim_periodo,
    codigo_inei              VARCHAR(12) NOT NULL REFERENCES gold.dim_universidad,
    hhi                      NUMERIC(8, 1) NOT NULL,
    programas                INTEGER     NOT NULL,
    matriculados_universidad INTEGER     NOT NULL,
    PRIMARY KEY (anio, codigo_inei)
);

-- GRANULARIDAD: una fila por anio x semestre x universidad x programa.
-- SIN ubicacion_sk: medido, DEPARTAMENTO_FILIAL viene vacio en el 100 % de las
-- filas de la fuente de egresados. Ver sql/gold/24_fct_egresados.sql.
CREATE TABLE gold.fct_egresados (
    anio               SMALLINT    NOT NULL REFERENCES gold.dim_periodo,
    semestre           SMALLINT    NOT NULL REFERENCES gold.dim_semestre,
    codigo_inei        VARCHAR(12) NOT NULL REFERENCES gold.dim_universidad,
    programa_sk        CHAR(32)    NOT NULL REFERENCES gold.dim_programa,
    egresados          INTEGER     NOT NULL,
    nota_promedio      NUMERIC(5, 2),
    creditos_aprobados NUMERIC(8, 1),
    PRIMARY KEY (anio, semestre, programa_sk)
);

-- GRANULARIDAD: una fila por anio x semestre x universidad.
-- GRANO MAS GRUESO, DECLARADO: la fuente de docentes no trae programa ni la
-- ubicacion del local donde se ensena. Ver sql/gold/25_fct_docentes.sql.
CREATE TABLE gold.fct_docentes (
    anio                     SMALLINT    NOT NULL REFERENCES gold.dim_periodo,
    semestre                 SMALLINT    NOT NULL REFERENCES gold.dim_semestre,
    codigo_inei              VARCHAR(12) NOT NULL REFERENCES gold.dim_universidad,
    docentes                 INTEGER     NOT NULL,
    docentes_tiempo_completo INTEGER     NOT NULL,
    docentes_posgrado        INTEGER     NOT NULL,
    docentes_ordinarios      INTEGER     NOT NULL,
    PRIMARY KEY (anio, semestre, codigo_inei)
);

-- GRANULARIDAD: una fila por anio de resolucion x universidad.
-- La llave se resuelve por igualdad de nombre normalizado, no por codigo: la
-- fuente no trae codigo INEI. Ver sql/gold/26_fct_titulos.sql y el control #11.
CREATE TABLE gold.fct_titulos (
    anio                  SMALLINT    NOT NULL REFERENCES gold.dim_periodo,
    codigo_inei           VARCHAR(12) NOT NULL REFERENCES gold.dim_universidad,
    titulos               INTEGER     NOT NULL,   -- eventos de titulacion
    personas              INTEGER     NOT NULL,   -- personas distintas: lo comparable con egresados,
    bachilleres           INTEGER     NOT NULL,
    titulados             INTEGER     NOT NULL,
    anios_estudio_mediana NUMERIC(5, 2),
    PRIMARY KEY (anio, codigo_inei)
);
