"""
Tests fuer utils/secrets.py.

Statt der echten Secrets-Datenbank steht hier ein SQLite im Arbeitsspeicher mit
derselben Tabellenform. Das ist Absicht: Die echten Zugangsdaten sollen in
keinem Testlauf auftauchen, und die Rolle `bot_secrets_reader` gehoert dem Bot,
nicht der Entwicklungsumgebung.

**Was das beweist:** die Suchlogik, den Zwischenspeicher, das Verhalten bei
fehlenden und abgeschalteten Eintraegen, und dass kein Wert ins Log geraet.
**Was das nicht beweist:** dass die Rechte in Postgres richtig gesetzt sind.
Dafuer gibt es die Gegenprobe am Ende von deploy/secrets_db.sql.
"""

import logging

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from utils import secrets

# Die fuer den Test noetige Teilmenge von deploy/secrets_db.sql.
TABELLE = """
CREATE TABLE credentials (
    id        INTEGER PRIMARY KEY,
    service   TEXT NOT NULL,
    scope     TEXT NOT NULL DEFAULT '*',
    key_name  TEXT NOT NULL,
    value     TEXT NOT NULL,
    note      TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    UNIQUE (service, scope, key_name)
);
"""

EINTRAEGE = [
    ("discord", "discord-profession-helper-app-token", "token", "token-berufe", 1),
    ("discord", "discord-group-helper-app-token", "token", "token-raid", 1),
    # Ein gewechselter Schluessel: der alte bleibt stehen, nur abgeschaltet.
    ("raid-helper", "123456789", "api_key", "api-key-alt", 0),
    ("openai", "*", "api_key", "kein-server-bezug", 1),
]


@pytest.fixture(autouse=True)
def secrets_datenbank(monkeypatch):
    """
    Haengt utils.secrets an ein SQLite im Arbeitsspeicher.

    StaticPool, weil ':memory:' sonst pro Verbindung eine **neue, leere**
    Datenbank ist - die Tabelle waere beim naechsten connect() wieder weg.
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.begin() as verbindung:
        verbindung.execute(text(TABELLE))
        for service, scope, key_name, wert, aktiv in EINTRAEGE:
            verbindung.execute(
                text(
                    "INSERT INTO credentials (service, scope, key_name, value, is_active)"
                    " VALUES (:s, :sc, :k, :v, :a)"
                ),
                {"s": service, "sc": scope, "k": key_name, "v": wert, "a": aktiv},
            )

    monkeypatch.setattr(secrets, "_engine", engine)
    secrets.clear_cache()
    yield engine
    secrets.clear_cache()


def test_findet_den_richtigen_token() -> None:
    assert secrets.get_discord_token("discord-profession-helper-app-token") == "token-berufe"
    assert secrets.get_discord_token("discord-group-helper-app-token") == "token-raid"


def test_scope_als_zahl_und_als_text_treffen_beide() -> None:
    """Discord-IDs sind Zahlen, in der Tabelle steht Text."""
    assert secrets.get_secret("openai", "api_key") == "kein-server-bezug"
    # Der abgeschaltete Eintrag bleibt in beiden Schreibweisen unsichtbar.
    assert secrets.get_secret("raid-helper", "api_key", 123456789) is None
    assert secrets.get_secret("raid-helper", "api_key", "123456789") is None


def test_abgeschalteter_eintrag_wird_nicht_geliefert(secrets_datenbank) -> None:
    """
    Schluesselwechsel: is_active = 0 statt Loeschen. Wuerde die Abfrage das
    uebersehen, benutzte der Bot nach einer Rotation weiter den alten Schluessel -
    und der Fehler saehe aus wie ein Problem beim Anbieter.
    """
    assert secrets.get_secret("raid-helper", "api_key", "123456789") is None

    secrets.clear_cache()
    with secrets_datenbank.begin() as verbindung:
        verbindung.execute(text("UPDATE credentials SET is_active = 1 WHERE service='raid-helper'"))
    assert secrets.get_secret("raid-helper", "api_key", "123456789") == "api-key-alt"


def test_unbekannter_eintrag_ergibt_none() -> None:
    assert secrets.get_secret("gibt-es-nicht", "token") is None
    assert secrets.get_secret("discord", "gibt-es-nicht", "app") is None


def test_require_secret_nennt_die_drei_koordinaten() -> None:
    """
    Ohne service, scope und key_name in der Meldung sucht man im falschen
    Eintrag - und die Tabelle ist per Definition nicht die, in die man mal eben
    hineinschaut.
    """
    with pytest.raises(RuntimeError) as fehler:
        secrets.require_secret("discord", "token", "app-die-es-nicht-gibt")
    meldung = str(fehler.value)
    assert "discord" in meldung
    assert "app-die-es-nicht-gibt" in meldung
    assert "token" in meldung
    assert "INSERT INTO credentials" in meldung


def test_zweiter_zugriff_kommt_aus_dem_zwischenspeicher(secrets_datenbank) -> None:
    assert secrets.get_discord_token("discord-profession-helper-app-token") == "token-berufe"

    with secrets_datenbank.begin() as verbindung:
        verbindung.execute(text("DELETE FROM credentials"))

    # Trotz leerer Tabelle: Der Wert kommt aus dem Zwischenspeicher.
    assert secrets.get_discord_token("discord-profession-helper-app-token") == "token-berufe"
    secrets.clear_cache()
    with pytest.raises(RuntimeError):
        secrets.get_discord_token("discord-profession-helper-app-token")


def test_der_wert_landet_nicht_im_log(caplog) -> None:
    """Die wichtigste Zusicherung: Logs bleiben 30 Tage liegen."""
    with caplog.at_level(logging.DEBUG):
        secrets.get_discord_token("discord-profession-helper-app-token")
        secrets.get_secret("gibt-es-nicht", "token")
    assert "token-berufe" not in caplog.text
    # Die Koordinaten duerfen drinstehen - ohne sie ist das Log nutzlos.
    assert "discord-profession-helper-app-token" in caplog.text
