"""
Gemeinsame Basis der Auswertungsskripte in diesem Ordner.

Alle Skripte hier lesen ausschliesslich die bereits heruntergeladenen Dateien unter
data/probe/ - sie senden nie einen Request. Neue Rohdaten holt tools/probe_listing.py.
"""

import json
from pathlib import Path

# __file__ = tools/analysis/_probe_data.py  ->  parents[2] = profession-helper-app/
PROBE_DIR = Path(__file__).resolve().parents[2] / "data" / "probe"


def load(filename: str) -> list[dict]:
    """Laedt eine Probe-Datei, z. B. 'tailoring.de.json'."""
    path = PROBE_DIR / filename
    if not path.exists():
        raise SystemExit(
            f"{path} fehlt.\n"
            f"Erst holen mit: uv run python tools/probe_listing.py --out data/probe/{filename}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_html(filename: str) -> str:
    """
    Laedt eine gecachte Roh-Seite, z. B. 'enchanting.de.html'.

    Die HTML-Dateien legt tools/probe_all.py ab; sie sind gitignored, auf einem
    frischen Klon muessen sie also erst geholt werden.
    """
    path = PROBE_DIR / filename
    if not path.exists():
        raise SystemExit(
            f"{path} fehlt.\nErst holen mit: uv run python tools/probe_all.py"
        )
    return path.read_text(encoding="utf-8")


def recipes_only(entries: list[dict]) -> list[dict]:
    """
    Entfernt die Berufsrang-Eintraege - das sind keine Rezepte.

    Marker: weder 'reagents' noch 'creates'. Bei Schneiderei trifft das exakt die 8
    Rang-Eintraege und keines der 469 echten Rezepte.

    Nicht geeignet als Marker waere 'rank': vier echte Forever-Rezepte tragen es
    ebenfalls (Spinnrad 'Stufe 2', Webstuhl 'Stufe 4', Fraktionsbanner 'Stufe 1').
    Ebenso wenig 'learnedat == 9999' - das haben 11 Eintraege, nicht 8.
    """
    return [e for e in entries if "reagents" in e or "creates" in e]


def is_forever(entry: dict) -> bool:
    """Neue Forever-Zauber liegen im ID-Bereich ab ~400.000, Classic darunter."""
    return entry["id"] >= 400_000
