"""
Tests fuer den Vergleich in tools/check_schema.py.

Das Skript selbst braucht eine Datenbank; die Vergleichslogik nicht. Genau die
wird hier geprueft - ein Schema-Waechter, der nichts findet, ist schlimmer als
keiner, weil er Sicherheit vortaeuscht.

Die Modellseite ist echt (die `guilds`-Tabelle aus services/models.py), die
Datenbankseite ist nachgebaut: So sieht `inspect(engine).get_columns()` aus.
"""

from sqlalchemy import BigInteger, DateTime, Text

from services.database import Base
from tools.check_schema import pruefe_tabelle

GUILDS = Base.metadata.tables["guilds"]

# So, wie SQLAlchemy die Tabelle aus der laufenden Datenbank zurueckliest.
PASSEND = [
    {"name": "id", "type": BigInteger(), "nullable": False},
    {"name": "name", "type": Text(), "nullable": False},
    {"name": "created_at", "type": DateTime(timezone=True), "nullable": False},
]


def test_keine_abweichung_wenn_alles_passt() -> None:
    assert pruefe_tabelle("guilds", GUILDS, PASSEND) == []


def test_fehlende_spalte_wird_gemeldet() -> None:
    ohne_name = [s for s in PASSEND if s["name"] != "name"]
    meldungen = pruefe_tabelle("guilds", GUILDS, ohne_name)
    assert len(meldungen) == 1
    assert "'name' fehlt in der Datenbank" in meldungen[0]


def test_unbekannte_spalte_wird_gemeldet() -> None:
    mit_extra = [*PASSEND, {"name": "drift", "type": Text(), "nullable": True}]
    meldungen = pruefe_tabelle("guilds", GUILDS, mit_extra)
    assert len(meldungen) == 1
    assert "'drift' kennt das Modell nicht" in meldungen[0]


def test_falscher_typ_wird_gemeldet() -> None:
    """Der haeufigste stille Fehler: bigint im Schema, Integer im Modell."""
    falscher_typ = [
        {"name": "id", "type": Text(), "nullable": False},
        *[s for s in PASSEND if s["name"] != "id"],
    ]
    meldungen = pruefe_tabelle("guilds", GUILDS, falscher_typ)
    assert len(meldungen) == 1
    assert "Typ BIGINT im Modell, TEXT in der Datenbank" in meldungen[0]


def test_abweichende_nullability_wird_gemeldet() -> None:
    nullable_name = [
        {"name": "name", "type": Text(), "nullable": True},
        *[s for s in PASSEND if s["name"] != "name"],
    ]
    meldungen = pruefe_tabelle("guilds", GUILDS, nullable_name)
    assert len(meldungen) == 1
    assert "nullable=False im Modell, True in der Datenbank" in meldungen[0]


def test_zeitzone_wird_nicht_uebersehen() -> None:
    """
    `timestamp` und `timestamptz` sind in Postgres verschiedene Typen, und der
    Unterschied faellt erst auf, wenn Zeiten um Stunden danebenliegen.
    """
    ohne_zeitzone = [
        {"name": "created_at", "type": DateTime(timezone=False), "nullable": False},
        *[s for s in PASSEND if s["name"] != "created_at"],
    ]
    meldungen = pruefe_tabelle("guilds", GUILDS, ohne_zeitzone)
    assert len(meldungen) == 1
    assert "created_at" in meldungen[0]
