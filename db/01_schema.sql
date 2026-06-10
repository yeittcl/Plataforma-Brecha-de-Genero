BEGIN;

CREATE TYPE genero_enum AS ENUM ('male', 'female', 'unknown');

CREATE TYPE posicion_enum AS ENUM ('first', 'second', 'penultimate', 'last', 'other');

CREATE TABLE "Region" (
    "Id"     SERIAL       PRIMARY KEY,
    "Nombre" VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE "Pais" (
    "Id"        SERIAL       PRIMARY KEY,
    "Nombre"    VARCHAR(150) NOT NULL,
    "ISO3"      CHAR(3)      NULL,
    "Id_Region" INT          NULL,
    UNIQUE ("Nombre"),
    UNIQUE ("ISO3"),
    FOREIGN KEY ("Id_Region") REFERENCES "Region"("Id") ON DELETE SET NULL
);

CREATE TABLE "Area" (
    "Id"     SERIAL      PRIMARY KEY,
    "Nombre" VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE "Categoria" (
    "Id"     SERIAL       PRIMARY KEY,
    "Nombre" VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE "Area_Categoria" (
    "IdArea"      INT NOT NULL,
    "IdCategoria" INT NOT NULL,
    PRIMARY KEY ("IdArea", "IdCategoria"),
    FOREIGN KEY ("IdArea")      REFERENCES "Area"("Id")      ON DELETE CASCADE,
    FOREIGN KEY ("IdCategoria") REFERENCES "Categoria"("Id") ON DELETE CASCADE
);

CREATE TABLE "Editorial" (
    "Id"          SERIAL       PRIMARY KEY,
    "Nombre"      VARCHAR(200) NOT NULL UNIQUE,
    "OpenAlex_Id" VARCHAR(100) NULL UNIQUE,
    "Id_Pais"     INT          NULL,
    FOREIGN KEY ("Id_Pais") REFERENCES "Pais"("Id") ON DELETE SET NULL
);

CREATE TABLE "Journal" (
    "Id"           SERIAL       PRIMARY KEY,
    "Nombre"       VARCHAR(300) NOT NULL,
    "ISSN"         VARCHAR(20)  NULL,
    "Id_Editorial" INT          NULL,
    UNIQUE ("Nombre"),
    FOREIGN KEY ("Id_Editorial") REFERENCES "Editorial"("Id") ON DELETE SET NULL
);

CREATE TABLE "Factor_Impacto" (
    "Id"         SERIAL PRIMARY KEY,
    "Año"        INT    NOT NULL,
    "Valor"      FLOAT  NOT NULL,
    "Id_Journal" INT    NOT NULL,
    FOREIGN KEY ("Id_Journal") REFERENCES "Journal"("Id") ON DELETE CASCADE
);

CREATE TABLE "Posicion" (
    "Id"              SERIAL        PRIMARY KEY,
    "PosicionInteres" posicion_enum NOT NULL UNIQUE
);

CREATE TABLE "Investigador" (
    "Id"           SERIAL       PRIMARY KEY,
    "Nombre"       VARCHAR(150) NOT NULL,
    "Genero"       genero_enum  NOT NULL,
    "Probabilidad" FLOAT        NOT NULL,
    UNIQUE ("Nombre")
);

CREATE TABLE "Paper" (
    "Id"                BIGSERIAL    PRIMARY KEY,
    "Año"               INT          NOT NULL,
    "Id_Journal"        INT          NOT NULL,
    "Id_Pais"           INT          NOT NULL,
    "Id_Categoria"      INT          NOT NULL,
    "Doi"               VARCHAR(200) NULL UNIQUE,
    FOREIGN KEY ("Id_Journal")   REFERENCES "Journal"("Id")    ON DELETE RESTRICT,
    FOREIGN KEY ("Id_Pais")      REFERENCES "Pais"("Id")       ON DELETE RESTRICT,
    FOREIGN KEY ("Id_Categoria") REFERENCES "Categoria"("Id") ON DELETE RESTRICT
);

CREATE TABLE "Contribucion" (
    "IdPaper"         BIGINT NOT NULL,
    "IdInvestigador"  INT    NOT NULL,
    "PosicionOrdinal" INT    NOT NULL,
    "Id_Posicion"     INT    NOT NULL,
    PRIMARY KEY ("IdPaper", "IdInvestigador", "PosicionOrdinal"),
    FOREIGN KEY ("IdPaper")        REFERENCES "Paper"("Id")        ON DELETE CASCADE,
    FOREIGN KEY ("IdInvestigador") REFERENCES "Investigador"("Id") ON DELETE RESTRICT,
    FOREIGN KEY ("Id_Posicion")    REFERENCES "Posicion"("Id")     ON DELETE RESTRICT
);

CREATE INDEX "IX_Paper_Año"                    ON "Paper" ("Año");
CREATE INDEX "IX_Paper_Id_Journal"             ON "Paper" ("Id_Journal");
CREATE INDEX "IX_Paper_Id_Pais"                ON "Paper" ("Id_Pais");
CREATE INDEX "IX_Paper_Id_Categoria"           ON "Paper" ("Id_Categoria");
CREATE INDEX "IX_Contribucion_IdInvestigador"  ON "Contribucion" ("IdInvestigador");
CREATE INDEX "IX_Contribucion_Id_Posicion"     ON "Contribucion" ("Id_Posicion");
CREATE INDEX "IX_Factor_Impacto_Id_Journal_Año" ON "Factor_Impacto" ("Id_Journal", "Año");

COMMIT;
