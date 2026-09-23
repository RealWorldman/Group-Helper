"""
Liefert der Scrape die Zauberbeschreibung mit Zahlenwerten?

Das ist Risiko 3 aus dem Plan und entscheidet ueber die Fragenklasse
"+35 Beweglichkeit": Der Zahlenwert steht nicht im Rezeptnamen
("Handschuhe - Ueberragende Beweglichkeit"), sondern nur in der Beschreibung.

Befund: Die Beschreibung steckt in derselben Seite, die probe_all.py ohnehin holt -
in einem zweiten Datenblock `WH.Gatherer.addData(6, <locale>, {...})` neben
`var listviewspells`. Ein zusaetzlicher Request pro Zauber ist also nicht noetig.

Gelesen wird hier aus <beruf>.de.spells.json, nicht aus dem HTML: Die Roh-Seiten sind
gitignored, die JSON-Dateien nicht.
"""

import re

from _probe_data import PROBE_DIR, load, load_mapping, recipes_only


def description_of(record: dict) -> str:
    """
    Holt die Beschreibung, ohne die Sprache zu kennen.

    Wowhead haengt das Sprachkuerzel an den Feldnamen (`description_dede`,
    `description_enus`). Ein fest verdrahteter Name waere genau so ein
    stillschweigender Fehlschlag, wie er uns bei den leeren Daten schon passiert ist.
    """
    for key, value in record.items():
        if key.startswith("description_"):
            return value or ""
    return ""


def analyse(profession: str) -> tuple[int, int, int, int]:
    """Zaehlt fuer einen Beruf, wie weit die Beschreibung traegt."""
    entries = recipes_only(load(f"{profession}.de.json"))
    spells = load_mapping(f"{profession}.de.spells.json")

    known = [e for e in entries if str(e["id"]) in spells]
    described = [e for e in known if description_of(spells[str(e["id"])])]
    with_number = [
        e for e in described if re.search(r"\d", description_of(spells[str(e["id"])]))
    ]
    return len(entries), len(known), len(described), len(with_number)


def show_samples(profession: str, needle: str, limit: int = 6) -> None:
    """Zeigt Rezepte, deren Name den Suchbegriff enthaelt, mit ihrer Beschreibung."""
    entries = recipes_only(load(f"{profession}.de.json"))
    spells = load_mapping(f"{profession}.de.spells.json")

    print(f"\n=== Stichprobe {profession}: Name enthaelt '{needle}' ===")
    hits = [e for e in entries if needle.lower() in e["name"].lower()]
    for entry in hits[:limit]:
        text = description_of(spells.get(str(entry["id"]), {})) or "(keine Beschreibung)"
        print(f"  {entry['id']:>8}  {entry['name']}")
        print(f"            -> {text}")


def main() -> None:
    professions = sorted(p.name.removesuffix(".de.json") for p in PROBE_DIR.glob("*.de.json"))
    if not professions:
        raise SystemExit(
            f"Keine *.de.json in {PROBE_DIR} - erst holen mit: uv run python tools/probe_all.py"
        )

    print(f"{'beruf':<16} {'rezepte':>8} {'im block':>9} {'beschrieben':>12} {'mit zahl':>9}")
    for profession in professions:
        total, known, described, with_number = analyse(profession)
        print(
            f"{profession:<16} {total:>8} {known:>9} {described:>12} {with_number:>9}"
            f"   ({100 * described / total:.1f} % beschrieben)"
        )

    # Die Beispielfrage aus dem Plan haengt an genau diesem Fall: Der Name nennt
    # "Ueberragende Beweglichkeit", die Zahl steht nur in der Beschreibung.
    show_samples("enchanting", "Beweglichkeit")


if __name__ == "__main__":
    main()
