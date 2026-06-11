-- ============================================================================
-- ClickHouse DW Schema — Memoria
-- ============================================================================
-- See DATAWAREHOUSE.md for the full architectural rationale.
-- Star schema: 1 fact table (Fact_Paper) + 5 dimensions.
-- Granularity: 1 row = 1 paper with precalculated gender flags.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Dim_Geografica
-- ----------------------------------------------------------------------------
-- Country + region consolidated (avoids snowflaking Region).
-- Loaded from Postgres.Pais JOIN Region.
CREATE TABLE IF NOT EXISTS Dim_Geografica (
    IdGeo         UInt32,
    NombrePais    String,
    NombreRegion  String
) ENGINE = MergeTree()
  ORDER BY IdGeo;


-- ----------------------------------------------------------------------------
-- Dim_Tiempo
-- ----------------------------------------------------------------------------
-- One row per year. Hito is nullable (no predefined events).
CREATE TABLE IF NOT EXISTS Dim_Tiempo (
    IdTiempo  UInt16,
    `Año`     UInt16,
    Decada    String,
    Siglo     String,
    Hito      Nullable(String)
) ENGINE = MergeTree()
  ORDER BY IdTiempo;


-- ----------------------------------------------------------------------------
-- Dim_Area
-- ----------------------------------------------------------------------------
-- Area + category desnormalized (1 row per Area-Categoria pair = 36 rows).
CREATE TABLE IF NOT EXISTS Dim_Area (
    IdArea           UInt16,
    NombreArea       String,
    NombreCategoria  String
) ENGINE = MergeTree()
  ORDER BY IdArea;


-- ----------------------------------------------------------------------------
-- Dim_Journal
-- ----------------------------------------------------------------------------
-- Journal + editorial denormalized. NO FactorImpacto here.
-- (See Dim_FactorImpacto for historical SJR.)
CREATE TABLE IF NOT EXISTS Dim_Journal (
    IdJournal        UInt32,
    NombreJournal    String,
    NombreEditorial  Nullable(String)
) ENGINE = MergeTree()
  ORDER BY IdJournal;


-- ----------------------------------------------------------------------------
-- Dim_FactorImpacto
-- ----------------------------------------------------------------------------
-- Historical SJR per (journal, year). 1 row per year per journal.
-- Partitioned by year for pruning.
CREATE TABLE IF NOT EXISTS Dim_FactorImpacto (
    IdFactorImpacto  UInt64,
    IdJournal        UInt32,
    `Año`            UInt16,
    SJR              Float32
) ENGINE = MergeTree()
  PARTITION BY `Año`
  ORDER BY (IdJournal, `Año`);


-- ----------------------------------------------------------------------------
-- Fact_Paper
-- ----------------------------------------------------------------------------
-- Grain: 1 row = 1 paper. Flags precalculated in ETL.
-- All flags are 0/1 UInt8 to minimize storage.
CREATE TABLE IF NOT EXISTS Fact_Paper (
    IdPaper        UInt64,
    IdTiempo       UInt16,
    IdGeo          UInt32,
    IdJournal      UInt32,
    IdArea         UInt16,
    Mujer_primera  UInt8,
    Mujer_penult   UInt8,
    Mujer_ult      UInt8,
    Hay_mujeres    UInt8,
    Mujer_Autora   UInt8
) ENGINE = MergeTree()
  PARTITION BY IdTiempo
  ORDER BY (IdTiempo, IdGeo, IdJournal, IdArea, IdPaper);
