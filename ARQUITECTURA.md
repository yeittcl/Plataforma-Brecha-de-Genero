# Arquitectura de Base de Datos Relacional (Sistema Origen)

Este documento describe el modelo de datos relacional transaccional que almacena
la información de publicaciones científicas (papers), investigadores y revistas.
El modelo es deliberadamente minimalista: una sola fila canónica por entidad, sin
redundancia entre tablas de "auditoría" y tablas de "trabajo".

## Historial de decisiones (resumen)

- `Investigador` se deduplica por `firstname`; `lastname` y `ORCID` se descartan.
- `Referencia Investigador` se elimina (redundante con `Investigador` deduplicado).
- `Factor_Impacto` usa `Año` único (SJR publica por año natural, no por vigencia).
- `Editorial` referencia `Id_Pais` para evitar duplicación del catálogo de países.
- `Paper` guarda solo `doi` como identificador externo; `pubmed_id` y `dblp_key`
  se descartan porque `doi` cubre la necesidad de trazabilidad externa.
- `NumComparaciones` (conteo de apariciones del nombre) no se persiste; se
  recalcula con un `GROUP BY` en SQL cuando se necesite.

## Convenciones de hygiene (ETL)

- Los nombres se normalizan a `firstname` antes de cargar. Si la fuente trae
  `lastname` o nombre completo, **se descartan** y solo persiste el `firstname`
  en `Investigador.Nombre`. Esto implica que dos autores distintos con el mismo
  `firstname` se colapsan en la misma fila (limitación conocida y aceptada).
- El typo heredado de los CSVs `fist` (en lugar de `first`) se mapea a `first`
  en el ETL antes de poblar `Posicion.PosicionInteres`.
- Los países en `country` (texto libre) se joinean con `Pais.Nombre`
  (case-insensitive, trim). Si no hay match, la fila va a un `Pais.Nombre='Unknown'`.

## Tablas y Atributos

### 1. Entidades de Publicación

**Editorial**

* `Id` (PK, INT): Identificador único de la editorial.
* `Nombre` (VARCHAR, UNIQUE): Nombre de la editorial (deduplicación por nombre).
* `Id_Pais` (FK, INT NULL): País de origen de la editorial (referencia al mismo
  catálogo que `Pais`, evita duplicación).

**Journal**

* `Id` (PK, INT): Identificador único de la revista.
* `Nombre` (VARCHAR): Nombre de la revista.
* `Id_Editorial` (FK, INT NULL): Editorial a la que pertenece (1..n).

**Factor_Impacto**

* `Id` (PK, INT): Identificador único.
* `Año` (INT): Año natural del factor. SJR publica un valor por año, no por
  vigencia; una revista puede tener varias filas (una por año disponible).
* `Valor` (FLOAT): Valor del SJR para ese año.
* `Id_Journal` (FK, INT): Revista asociada.

### 2. Entidades de Clasificación (Áreas y Categorías)

**Area**

* `Id` (PK, INT): Área de estudio de alto nivel.
* `Nombre` (VARCHAR): Nombre del área. **Valores válidos: `CS`, `BIO`, `CHEM`,
  `EARTH`, `PHYS`**.

**Categoria**

* `Id` (PK, INT): Categoría específica dentro de un área.
* `Nombre` (VARCHAR): Nombre de la categoría (término MeSH para PubMed;
  `Computer` para DBLP).

**Area-Categoria** (Tabla Intermedia)

* `IdArea` (PK/FK, INT): Referencia a `Area`.
* `IdCategoria` (PK/FK, INT): Referencia a `Categoria`.
* Restricción lógica: cada `IdCategoria` pertenece a **exactamente un** `IdArea`.

### 3. Entidades Geográficas

**Region**

* `Id` (PK, INT): Región (continente o subcontinente).
* `Nombre` (VARCHAR): Nombre de la región.

**Pais**

* `Id` (PK, INT): País.
* `Nombre` (VARCHAR): Nombre del país.
* `ISO3` (VARCHAR NULL): Código ISO 3166-1 alpha-3.
* `Id_Region` (FK, INT NULL): Región a la que pertenece.

### 4. Entidades Centrales (Paper y Autores)

**Paper**

* `Id` (PK, BIGSERIAL): Identificador surrogate interno.
* `Titulo` (VARCHAR): Título de la publicación.
* `Año` (INT): Año de publicación.
* `Fecha_Publicacion` (DATE NULL): Fecha completa cuando esté disponible
  (PubMed la trae a nivel de día; DBLP solo tiene año).
* `Id_Journal` (FK, INT): Revista donde se publicó.
* `Id_Pais` (FK, INT): País de la publicación.
* `Id_Categoria` (FK, INT): Categoría principal del paper.
* `doi` (VARCHAR NULL): DOI como identificador externo. Único cuando existe.

> Nota: el `Area` de un paper se obtiene por JOIN entre
> `Paper.Id_Categoria → Categoria.Id → Area_Categoria.IdCategoria → Area.Id`.
> No se desnormaliza en `Paper` para preservar la normalización.

**Investigador**

* `Id` (PK, INT): Identificador único.
* `Nombre` (VARCHAR): Firstname (único dato de nombre que se guarda). Si la
  fuente trae `lastname` o nombre completo, **se descartan** — solo persiste el
  `firstname`. Esto implica que dos autores distintos con el mismo `firstname`
  se colapsan en la misma fila.
* `Genero` (VARCHAR): Género inferido (`male`, `female`, `unknown`).
* `Probabilidad` (FLOAT): Certeza de la inferencia de género.

**Posicion**

* `Id` (PK, INT): Identificador único.
* `PosicionInteres` (VARCHAR): Etiqueta de posición. Valores: `first`, `second`,
  `penultimate`, `last`, `other`.

**Contribucion** (Tabla Intermedia)

* `IdPaper` (PK/FK, INT): Referencia a `Paper`.
* `IdInvestigador` (PK/FK, INT): Referencia a `Investigador`.
* `PosicionOrdinal` (INT): Posición exacta en la lista de autores (0, 1, 2, ...).
* `Id_Posicion` (FK, INT): Etiqueta de `PosicionInteres`.

## Catálogo Area–Categoria (36 pares)

| Area | Categoria | Origen |
|------|-----------|--------|
| BIO  | Anatomy | PubMed (MeSH) |
| BIO  | Biochemistry | PubMed (MeSH) |
| BIO  | Biology | PubMed (MeSH) |
| BIO  | Biophysics | PubMed (MeSH) |
| BIO  | Biotechnology | PubMed (MeSH) |
| BIO  | Chronobiology Discipline | PubMed (MeSH) |
| BIO  | Neurosciences | PubMed (MeSH) |
| BIO  | Pharmacology | PubMed (MeSH) |
| BIO  | Physiology | PubMed (MeSH) |
| BIO  | Toxicology | PubMed (MeSH) |
| CHEM | Cheminformatics | PubMed (MeSH) |
| CHEM | Chemistry Agricultural | PubMed (MeSH) |
| CHEM | Chemistry Analytic | PubMed (MeSH) |
| CHEM | Chemistry Clinical | PubMed (MeSH) |
| CHEM | Chemistry Inorganic | PubMed (MeSH) |
| CHEM | Chemistry Organic | PubMed (MeSH) |
| CHEM | Chemistry Pharmaceutical | PubMed (MeSH) |
| CHEM | Chemistry Physical | PubMed (MeSH) |
| CHEM | Computational Chemistry | PubMed (MeSH) |
| CHEM | Microchemistry | PubMed (MeSH) |
| EARTH| Astronomy | PubMed (MeSH) |
| EARTH| Geography | PubMed (MeSH) |
| EARTH| Geology | PubMed (MeSH) |
| EARTH| Limnology | PubMed (MeSH) |
| EARTH| Meteorology | PubMed (MeSH) |
| EARTH| Oceanography | PubMed (MeSH) |
| EARTH| Paleontology | PubMed (MeSH) |
| PHYS | Acoustics | PubMed (MeSH) |
| PHYS | Electronics | PubMed (MeSH) |
| PHYS | Health Physics | PubMed (MeSH) |
| PHYS | Magnetics | PubMed (MeSH) |
| PHYS | Mechanics | PubMed (MeSH) |
| PHYS | Nuclear Physics | PubMed (MeSH) |
| PHYS | Optics and Photonics | PubMed (MeSH) |
| PHYS | Rheology | PubMed (MeSH) |
| CS   | Computer | DBLP (categoría hardcodeada en `articleExtractor.py`) |

Totales: 5 Areas × 36 Categorias (10 BIO + 10 CHEM + 7 EARTH + 8 PHYS + 1 CS).

Este catálogo se materializa en `db/03_seed_categories.sql` mediante INSERTs
hardcodeados. Si en el futuro PubMed agrega una nueva sub-rama, basta agregar
el par correspondiente.
