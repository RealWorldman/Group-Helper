-- Einrichtung der Secrets-Datenbank.
--
-- Muss als Superuser laufen (`postgres`): group_helper_agent darf weder
-- Datenbanken noch Rollen anlegen - das ist geprueft, nicht vermutet.
--
-- Aufruf auf dem Pi:
--     sudo -u postgres psql -v ON_ERROR_STOP=1 -f secrets_db.sql
--
-- Zweck der Trennung: Der MCP-Server laeuft mit --access-mode=unrestricted als
-- group_helper_agent. Laegen die Secrets in `group-helper`, koennte jede
-- Agent-Sitzung alle Tokens im Klartext lesen. Eine eigene Datenbank mit eigener
-- Rolle verhindert das - aber nur, wenn die REVOKE-Zeilen unten stehen bleiben.

-- ---------------------------------------------------------------------------
-- 1. Datenbank
-- ---------------------------------------------------------------------------

-- CREATE DATABASE laeuft nicht in einer Transaktion, deshalb steht es allein.
CREATE DATABASE secrets;

-- **Der entscheidende Schritt, und keine Vorsichtsmassnahme.**
--
-- Eine neue Datenbank erbt die Vorgaberechte, und darin hat PUBLIC das Recht
-- CONNECT. Auf diesem Server nachgesehen (24.09.2026):
--
--   template1      datacl = {=c/postgres, postgres=CTc/postgres}   PUBLIC: CONNECT
--   group-helper   datacl = {postgres=CTc/..., group_helper_agent=Tc/...}   PUBLIC: nichts
--
-- Das `=c/postgres` in template1 ist genau dieses Recht; bei den bestehenden
-- Datenbanken wurde es bereits entzogen. Ohne diese Zeile koennte sich
-- group_helper_agent mit `secrets` verbinden und die Trennung waere wirkungslos.
REVOKE ALL ON DATABASE secrets FROM PUBLIC;

-- ---------------------------------------------------------------------------
-- 2. Rolle fuer die Bots
-- ---------------------------------------------------------------------------

-- Passwort vor dem Ausfuehren ersetzen. Es gehoert danach in die PGPASSFILE,
-- nicht in eine Datei im Repo.
CREATE ROLE bot_secrets_reader LOGIN PASSWORD 'HIER-EIN-PASSWORT-EINSETZEN';

GRANT CONNECT ON DATABASE secrets TO bot_secrets_reader;

-- ---------------------------------------------------------------------------
-- 3. Tabelle - ab hier in der neuen Datenbank
-- ---------------------------------------------------------------------------

\connect secrets

-- Auch hier: PUBLIC soll im Schema nichts duerfen.
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO bot_secrets_reader;

-- Ein Eintrag ist ueber drei Angaben eindeutig:
--   service  - woher stammt das Geheimnis  ('discord', 'raid-helper')
--   scope    - fuer welchen Server oder welche App gilt es
--   key_name - welches Feld               ('token', 'api_key')
--
-- Das bildet die bisherige JSON ab, ohne sie nachzubauen:
--   DISCORD     [{AppName: X,  DiscordToken: Y}] -> ('discord', X, 'token', Y)
--   RAID-HELPER [{ServerID: X, ApiKey: Y}]       -> ('raid-helper', X, 'api_key', Y)
CREATE TABLE credentials (
    id         bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    service    text        NOT NULL,
    -- '*' fuer Geheimnisse, die nicht pro Server anfallen. Ein eigener Wert
    -- statt NULL, damit UNIQUE greift: In Postgres gelten zwei NULL als
    -- verschieden, ein Duplikat kaeme also unbemerkt durch.
    scope      text        NOT NULL DEFAULT '*',
    key_name   text        NOT NULL,
    value      text        NOT NULL,
    -- Wofuer der Eintrag da ist. Bei Schluesseln, die man Jahre spaeter
    -- wiederfindet, ist das der Unterschied zwischen Rotieren und Raten.
    note       text,
    -- Schluesselwechsel ohne Loeschen: alten Eintrag auf false, neuen anlegen.
    is_active  boolean     NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (service, scope, key_name)
);

COMMENT ON TABLE credentials IS
    'Zugangsdaten der Gilden-Bots. Nur postgres schreibt hier, die Bots lesen.';

REVOKE ALL ON credentials FROM PUBLIC;
GRANT SELECT ON credentials TO bot_secrets_reader;

-- ---------------------------------------------------------------------------
-- 4. Gegenprobe
-- ---------------------------------------------------------------------------

-- Muss `false` liefern. Tut es das nicht, kommt group_helper_agent an die
-- Secrets und die Trennung ist nicht wirksam.
SELECT has_database_privilege('group_helper_agent', 'secrets', 'CONNECT')
       AS agent_darf_verbinden_muss_false;
