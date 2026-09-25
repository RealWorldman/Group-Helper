"""
Laufen services/models.py und die echte Datenbank noch zusammen?

Das Schema entsteht aus services/migrations.py, die Modelle bilden es nur ab -
also koennen beide auseinanderlaufen. Dieses Skript findet das, statt es im
Betrieb auffliegen zu lassen: Eine Spalte, die ein Modell kennt und die
Datenbank nicht, faellt sonst erst beim ersten SELECT auf, das sie anfasst.

Aufruf (braucht PROFESSION_DATABASE_URL):
    uv run python tools/check_schema.py

Exit-Code 1, wenn es Abweichungen gibt - damit ein Deployment-Skript daran
haengenbleiben kann.
"""

import sys
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# tools/ -> Projektwurzel, damit `services` und `config` importierbar sind.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import models  # noqa: E402, F401  - registriert die Modelle an Base
from services.database import Base, get_engine  # noqa: E402

# Wird von migrations.py selbst verwaltet und hat absichtlich kein Modell.
IGNORIERTE_TABELLEN = {"schema_version"}


def typ_als_text(typ) -> str:
    """
    Der Typ so, wie Postgres ihn schreiben wuerde.

    Ueber den Dialekt statt ueber die Python-Klasse: `Text` und `TEXT` sind
    verschiedene Objekte, aber dasselbe Datenbank-Typ. Der Vergleich soll
    Tippfehler finden, nicht Schreibweisen.
    """
    return typ.compile(dialect=postgresql.dialect())


def pruefe_tabelle(name: str, erwartet, vorhanden: list[dict]) -> list[str]:
    """Vergleicht eine Tabelle Spalte fuer Spalte und liefert die Abweichungen."""
    abweichungen = []
    ist = {spalte["name"]: spalte for spalte in vorhanden}
    soll = {spalte.name: spalte for spalte in erwartet.columns}

    for fehlend in sorted(soll.keys() - ist.keys()):
        abweichungen.append(f"  Spalte '{fehlend}' fehlt in der Datenbank")
    for ueberzaehlig in sorted(ist.keys() - soll.keys()):
        abweichungen.append(f"  Spalte '{ueberzaehlig}' kennt das Modell nicht")

    for spalte in sorted(soll.keys() & ist.keys()):
        modell, datenbank = soll[spalte], ist[spalte]
        if typ_als_text(modell.type) != typ_als_text(datenbank["type"]):
            abweichungen.append(
                f"  Spalte '{spalte}': Typ {typ_als_text(modell.type)} im Modell, "
                f"{typ_als_text(datenbank['type'])} in der Datenbank"
            )
        if modell.nullable != datenbank["nullable"]:
            abweichungen.append(
                f"  Spalte '{spalte}': nullable={modell.nullable} im Modell, "
                f"{datenbank['nullable']} in der Datenbank"
            )

    return abweichungen


def main() -> int:
    inspektor = inspect(get_engine())
    in_datenbank = set(inspektor.get_table_names()) - IGNORIERTE_TABELLEN
    in_modellen = set(Base.metadata.tables)

    probleme = []

    for fehlend in sorted(in_modellen - in_datenbank):
        probleme.append(f"{fehlend}: Tabelle fehlt in der Datenbank - Migration nicht gelaufen?")
    for ueberzaehlig in sorted(in_datenbank - in_modellen):
        probleme.append(f"{ueberzaehlig}: Tabelle ohne Modell - in models.py nachtragen?")

    for name in sorted(in_modellen & in_datenbank):
        abweichungen = pruefe_tabelle(name, Base.metadata.tables[name], inspektor.get_columns(name))
        if abweichungen:
            probleme.append(name + ":")
            probleme.extend(abweichungen)

    geprueft = len(in_modellen & in_datenbank)
    if probleme:
        print(f"{geprueft} Tabellen verglichen, Abweichungen gefunden:\n")
        print("\n".join(probleme))
        return 1

    print(f"{geprueft} Tabellen verglichen, Modelle und Datenbank stimmen ueberein.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
