"""
Schema-Migrationen ohne Alembic.

Der Plan begruendet das so: ein Betreiber, ein Deployment, taegliches Backup.
Eine Tabelle `schema_version` und nummerierte Schritte reichen - und man sieht
das vollstaendige DDL, statt es aus Modellen und Autogenerate zu erraten.

**Das SQL hier ist die Wahrheit, nicht services/models.py.** Die Modelle bilden
ab, was diese Migrationen angelegt haben. `Base.metadata.create_all()` wird
absichtlich nirgends aufgerufen: Sonst gaebe es zwei Quellen fuer dasselbe
Schema, die auseinanderlaufen koennen.

Regeln:

* Migrationen werden **angehaengt, nie geaendert.** Eine bereits angewendete
  Nummer ist auf dem Pi gelaufen; sie nachtraeglich zu bearbeiten heisst, dass
  frisches und gewachsenes Schema sich unterscheiden.
* Jede Migration laeuft in **einer** Transaktion. Postgres kann DDL
  transaktional - ein Fehler in der Mitte hinterlaesst also kein halbes Schema.

Anwenden:
    uv run python -m services.migrations
"""

import logging
import sys

from sqlalchemy import text

from services.database import get_engine

log = logging.getLogger(__name__)

# Die Versionstabelle selbst kann nicht Teil einer Migration sein - sie wird
# gebraucht, um zu wissen, welche Migration schon lief.
BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    integer     PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);
"""

M001_STAMMDATEN = """
-- Berufe als Stammdaten, nicht als Konstanten im Code: /beruf setzen bietet alle
-- primaeren Berufe an, die Rezept-Commands nur die mit Rezepten. Beide Listen
-- kommen aus dieser Tabelle.
CREATE TABLE professions (
    id            smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key           text     NOT NULL UNIQUE,
    name_de       text     NOT NULL,
    name_en       text     NOT NULL,
    -- Die Skill-Line-ID aus dem Wowhead-Feld `skill`, z. B. 197 fuer Schneiderei.
    -- Sie ist der Schluessel, ueber den der Katalog-Import Rezepte zuordnet.
    skill_line_id integer  NOT NULL UNIQUE,
    -- Der Slug der Berufsseite, z. B. 'tailoring'. Alle neun sind belegt,
    -- siehe tools/catalog_sources.md Abschnitt 1a.
    wowhead_slug  text     NOT NULL UNIQUE,
    is_primary    boolean  NOT NULL DEFAULT true,
    has_recipes   boolean  NOT NULL DEFAULT true,
    is_included   boolean  NOT NULL DEFAULT true
);

-- Discord-Snowflakes sind durchgaengig bigint. Das Nachbarprojekt nutzt Integer;
-- SQLite verzeiht das, Postgres nicht - und richtig ist es dort ebenso wenig.
CREATE TABLE guilds (
    id         bigint      PRIMARY KEY,
    name       text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE members (
    id              bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id        bigint      NOT NULL REFERENCES guilds (id) ON DELETE CASCADE,
    discord_user_id bigint      NOT NULL,
    display_name    text        NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (guild_id, discord_user_id)
);

-- Ein Mitglied hat mehrere Charaktere (Twinks). Ergebnisse werden spaeter nach
-- Mitglied gruppiert, nicht nach Charakter.
CREATE TABLE characters (
    id                bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id         bigint      NOT NULL REFERENCES members (id) ON DELETE CASCADE,
    guild_id          bigint      NOT NULL REFERENCES guilds (id) ON DELETE CASCADE,
    name              text        NOT NULL,
    -- Normalisiert von utils.textnorm.normalize(). Die Eindeutigkeit haengt an
    -- dieser Spalte, nicht an `name`: sonst waeren "Thrallmar" und "thrallmar"
    -- zwei Charaktere.
    name_norm         text        NOT NULL,
    realm             text        NOT NULL,
    faction           text        NOT NULL CHECK (faction IN ('alliance', 'horde')),
    -- Klasse heisst nicht `class`: das waere in Python ein Schluesselwort und
    -- als ORM-Attribut nicht schreibbar.
    wow_class         text,
    level             smallint    CHECK (level BETWEEN 1 AND 255),
    is_main           boolean     NOT NULL DEFAULT false,
    is_active         boolean     NOT NULL DEFAULT true,
    last_confirmed_at timestamptz,
    deleted_at        timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (guild_id, name_norm, realm)
);

CREATE TABLE character_professions (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    character_id   bigint      NOT NULL REFERENCES characters (id) ON DELETE CASCADE,
    profession_id  smallint    NOT NULL REFERENCES professions (id),
    -- Obergrenze grosszuegig: Forever hebt Skill-Kappen an, und ein zu enger
    -- CHECK waere eine Migration wert, die niemand vorhersieht.
    skill_level    smallint    NOT NULL CHECK (skill_level BETWEEN 0 AND 1200),
    skill_max      smallint    CHECK (skill_max BETWEEN 0 AND 1200),
    specialization text,
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (character_id, profession_id)
);

-- "Wer ist Verzauberer?" - der haeufigste Zugriff ueberhaupt, absteigend nach
-- Skill, damit die Besten ohne Sortierschritt oben stehen.
CREATE INDEX ix_charprof_prof_skill ON character_professions (profession_id, skill_level DESC);
CREATE INDEX ix_characters_guild_active ON characters (guild_id, is_active);
CREATE INDEX ix_characters_member ON characters (member_id);
"""

M002_BERUFE = """
-- Die neun Berufe im Scope. Slugs und skill_line_id sind im M0-Spike belegt,
-- siehe tools/catalog_sources.md Abschnitt 1a.
--
-- has_recipes ist bei allen neun `true`. Der Plan ging von sieben aus und wollte
-- Kraeuterkunde und Kuerschnerei nur fuer "wer kann mir Leder machen?" fuehren -
-- aber bei Forever stellen beide Gebaeude her (je drei Rezepte). Die Spalte
-- bleibt trotzdem: Sie ist Daten, keine Konstante im Code, und falls Forever die
-- Rezepte je zurueckzieht, ist das ein UPDATE statt eines Deployments.
INSERT INTO professions (key, name_de, name_en, skill_line_id, wowhead_slug, has_recipes) VALUES
    ('alchemy',        'Alchemie',          'Alchemy',        171, 'alchemy',        true),
    ('blacksmithing',  'Schmiedekunst',     'Blacksmithing',  164, 'blacksmithing',  true),
    ('enchanting',     'Verzauberkunst',    'Enchanting',     333, 'enchanting',     true),
    ('engineering',    'Ingenieurskunst',   'Engineering',    202, 'engineering',    true),
    ('herbalism',      'Kräuterkunde',      'Herbalism',      182, 'herbalism',      true),
    ('leatherworking', 'Lederverarbeitung', 'Leatherworking', 165, 'leatherworking', true),
    ('mining',         'Bergbau',           'Mining',         186, 'mining',         true),
    ('skinning',       'Kürschnerei',       'Skinning',       393, 'skinning',       true),
    ('tailoring',      'Schneiderei',       'Tailoring',      197, 'tailoring',      true);
"""

# Nummer -> (Beschreibung, SQL). Nur anhaengen.
MIGRATIONS: dict[int, tuple[str, str]] = {
    1: ("Stammdaten: Berufe, Gilden, Mitglieder, Charaktere", M001_STAMMDATEN),
    2: ("Die neun Berufe im Scope", M002_BERUFE),
}


def applied_versions(connection) -> set[int]:
    """Welche Migrationen sind auf dieser Datenbank schon gelaufen?"""
    rows = connection.execute(text("SELECT version FROM schema_version"))
    return {row[0] for row in rows}


def migrate() -> list[int]:
    """
    Wendet alle fehlenden Migrationen in aufsteigender Reihenfolge an.

    Gibt die Nummern zurueck, die dieser Lauf angewendet hat - leer, wenn das
    Schema schon aktuell war.
    """
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(BOOTSTRAP_SQL))
        schon_da = applied_versions(connection)

    angewendet = []
    for version in sorted(MIGRATIONS):
        if version in schon_da:
            continue
        beschreibung, sql = MIGRATIONS[version]
        log.info("Migration %03d wird angewendet: %s", version, beschreibung)
        # Eigene Transaktion pro Migration: Postgres kann DDL transaktional, ein
        # Fehler hinterlaesst also kein halbes Schema - und die bereits
        # gelaufenen Migrationen bleiben bestehen.
        with engine.begin() as connection:
            connection.exec_driver_sql(sql)
            connection.execute(
                text("INSERT INTO schema_version (version) VALUES (:v)"), {"v": version}
            )
        angewendet.append(version)

    return angewendet


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    angewendet = migrate()
    if angewendet:
        print(f"Angewendet: {', '.join(f'{v:03d}' for v in angewendet)}")
    else:
        print("Schema ist aktuell, nichts zu tun.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
