# Decisiones Arquitectónicas del Data Warehouse

Este documento define la arquitectura analítica diseñada para evaluar la brecha de género en la autoría de publicaciones científicas (áreas STEM), con un enfoque específico en la jerarquía funcional dentro de los equipos de investigación (primer y último autor).

## 1. Patrón Arquitectónico

Se ha optado por un **Modelo en Estrella (Star Schema)**. Este diseño desnormaliza la estructura transaccional de origen para optimizar el rendimiento de lectura, evitar operaciones de cruce (JOINs) costosas y facilitar la integración con herramientas de visualización y APIs (como FastAPI).

## 2. Granularidad del Modelo

La granularidad de la tabla de hechos es de **1 Fila = 1 Paper (Publicación)**.

En lugar de registrar cada contribución individual, el modelo consolida la información del equipo de investigación a nivel de publicación. Esto permite responder de forma inmediata a preguntas sobre liderazgo e inclusión femenina mediante banderas (flags) precalculadas durante el proceso de extracción, transformación y carga (ETL).

## 3. Tabla de Hechos: `Fact_Paper`

Esta tabla centraliza las métricas aditivas y booleanas (1 o 0) calculadas a partir de la lista de autores de cada publicación.

**Llaves Foráneas:**
* `IdTiempo` (INT): Referencia a Dim_Tiempo.
* `IdGeo` (INT): Referencia a Dim_Geografica.
* `IdJournal` (INT): Referencia a Dim_Journal.
* `IdArea` (INT): Referencia a Dim_Area.
* `IdFactorImpacto` (INT, NULL): Referencia a Dim_FactorImpacto (histórica por año).

**Métricas y Banderas (Flags):**
* `Mujer_primera` (INT): 1 si la primera autora es mujer, 0 en caso contrario.
* `Mujer_penult` (INT): 1 si la penúltima autora es mujer, 0 en caso contrario.
* `Mujer_ult` (INT): 1 si la última autora (generalmente el Investigador Principal) es mujer, 0 en caso contrario.
* `Hay_mujeres` (INT): 1 si existe al menos una mujer en cualquier posición de autoría en el paper, 0 en caso contrario.
* `Mujer_Autora` (INT): 1 si el paper tiene **una única autora y esa autora es mujer**, 0 en cualquier otro caso (autoría múltiple, autoría única masculina, o sin autoras mujeres). Es un indicador de publicaciones unipersonales de mujeres.

## 4. Dimensiones

Las dimensiones agrupan los ejes de análisis y consolidan tablas relacionales para evitar dependencias transitivas (Snowflaking).

### 4.1 Dim_Geografica

Consolida la información de país y región para facilitar análisis comparativos entre economías.

* `IdGeo` (PK, INT): Llave subrogada.
* `NombrePais` (VARCHAR): Nombre del país de publicación.
* `NombreRegion` (VARCHAR): Agrupación continental o subcontinental.

### 4.2 Dim_Tiempo

Permite evaluar la evolución temporal de la brecha y el impacto de hitos globales históricos.

* `IdTiempo` (PK, INT): Llave subrogada (formato YYYY).
* `Año` (INT): Año de publicación.
* `Decada` (VARCHAR): Década correspondiente (ej. "2010s").
* `Siglo` (VARCHAR): Siglo correspondiente.
* `Hito` (VARCHAR, NULLABLE): Eventos sociopolíticos relevantes asociados al año (ej. "Crisis 2008", "COVID-19"). **Nullable**: se puede poblar opcionalmente desde una tabla seed externa; por defecto queda NULL.

### 4.3 Dim_Area

Desnormaliza la jerarquía científica para visualizar en qué disciplina la brecha es más pronunciada.

* `IdArea` (PK, INT): Llave subrogada.
* `NombreArea` (VARCHAR): Área general del conocimiento (ej. STEM, Ciencias Médicas).
* `NombreCategoria` (VARCHAR): Subdisciplina específica.

### 4.4 Dim_Journal

Centraliza los datos de la vía de publicación para analizar la correlación entre prestigio e inclusión.

* `IdJournal` (PK, INT): Llave subrogada.
* `NombreJournal` (VARCHAR): Nombre de la revista científica.
* `NombreEditorial` (VARCHAR): Editorial matriz de la revista (denormalizada).

> **Nota**: `FactorImpacto` no se incluye en Dim_Journal. Se modela en una dimensión aparte (`Dim_FactorImpacto`) porque el SJR cambia por año y queremos análisis temporal.

### 4.5 Dim_FactorImpacto

Tabla histórica que modela la evolución del SJR de cada journal por año. Permite análisis de correlación entre prestigio (medido por SJR) y brecha de género a lo largo del tiempo.

* `IdFactorImpacto` (PK, INT): Llave subrogada.
* `IdJournal` (FK, INT): Referencia a Dim_Journal.
* `Año` (INT): Año del factor de impacto.
* `SJR` (FLOAT): Valor numérico del SJR para ese año.

## 5. Modelo Dimensional — Diagrama

```
                  Dim_Tiempo
                     |
                     v
   Dim_Geografica -> Fact_Paper <- Dim_Area
                     |
                     v
                 Dim_Journal
                     |
                     v
              Dim_FactorImpacto (1:N con Dim_Journal, una fila por año)
```

## 6. Decisiones del Pipeline ETL

* **Pre-cálculo de Jerarquía:** El script ETL en Python/Pandas será responsable de ordenar a los autores de cada publicación en origen y determinar las posiciones (primero, penúltimo, último).
* **Asignación Binaria:** Las métricas de `Fact_Paper` deben poblarse estrictamente con valores enteros (`1` o `0`) durante la transformación, garantizando que el motor de base de datos analítico (PostgreSQL) pueda ejecutar funciones de agregación (`SUM()`) a máxima velocidad para los rankings del frontend.
* **Cálculo de `Mujer_Autora`:** Indicador específico de publicaciones unipersonales femeninas. Se calcula en el ETL como `1` si y solo si el paper tiene exactamente 1 autor y ese autor es mujer. Es un caso más restringido que `Hay_mujeres`.
* **Full Refresh:** El script `etl/load_clickhouse.py` hace TRUNCATE + INSERT en cada ejecución, no es incremental. Esto simplifica el manejo de updates y garantiza consistencia con Postgres.
* **No se crean `Dim_Investigador` ni `Dim_Editorial` separadas** en esta versión. La editorial está denormalizada en `Dim_Journal` y el análisis por investigador individual puede hacerse con queries directas a `Postgres.Contribucion`. Si el futuro lo requiere, se agregan dimensiones adicionales.

## 7. Ejemplos de Queries Esperadas

```sql
-- Porcentaje de papers con mujer primera autora por país y década
SELECT
    g.NombrePais,
    t.Decada,
    ROUND(100.0 * SUM(f.Mujer_primera) / COUNT(*), 2) AS pct_mujer_primera
FROM Fact_Paper f
JOIN Dim_Geografica g ON g.IdGeo = f.IdGeo
JOIN Dim_Tiempo t ON t.IdTiempo = f.IdTiempo
GROUP BY g.NombrePais, t.Decada
ORDER BY t.Decada, pct_mujer_primera DESC;

-- Brecha de género por área y posición de autoría
SELECT
    a.NombreArea,
    SUM(f.Mujer_primera) AS n_mujer_primera,
    SUM(f.Mujer_ult)    AS n_mujer_ult,
    SUM(f.Mujer_penult) AS n_mujer_penult,
    COUNT(*)            AS n_papers
FROM Fact_Paper f
JOIN Dim_Area a ON a.IdArea = f.IdArea
GROUP BY a.NombreArea
ORDER BY n_papers DESC;

-- Correlación SJR con brecha de género
SELECT
    j.NombreJournal,
    fi.Año,
    fi.SJR,
    f.Mujer_primera,
    f.Mujer_ult
FROM Fact_Paper f
JOIN Dim_Journal j ON j.IdJournal = f.IdJournal
JOIN Dim_FactorImpacto fi ON fi.IdJournal = f.IdJournal AND fi.Año = f.IdTiempo
WHERE fi.SJR > 1.0
ORDER BY fi.SJR DESC, fi.Año;
```
