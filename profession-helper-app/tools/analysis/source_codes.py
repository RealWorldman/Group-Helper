"""
Was bedeuten die Zahlen im Feld 'source'?

Laeuft ueber alle Berufe unter data/probe/ und zeigt pro Beruf, welche Codes vorkommen.
Die Bedeutungen sind gegen die Trefferzahlen der Wowhead-Filter belegt, siehe
tools/catalog_sources.md Abschnitt 3. Taucht ein Code auf, der hier nicht steht, meldet
das Skript ihn als UNBEKANNT - er darf nicht stillschweigend als "kein Lehrer-Rezept"
durchrutschen.

Gelesen wird die deutsche Fassung. Das ist fast, aber nicht ganz gleichwertig: Von 2416
Eintraegen weicht genau einer ab - "Raeucherkerze" (1229705) hat auf Deutsch
source [4, 6] und auf Englisch gar kein source-Feld. Wowheads Crowdsourcing wird pro
Sprache gepflegt. Fuer diese Auswertung ist das zu vernachlaessigen, fuer den Import
nicht: Er soll die Codes beider Sprachen vereinigen, statt eine Sprache zu waehlen.
"""

from collections import Counter, defaultdict

from _probe_data import PROBE_DIR, load

# Code 2-21 belegt am Dropdown /forever/de/skill=197/schneiderei#recipes;source=<Quelle>,
# Code 1 ("Hergestellt") separat im Wowhead-WebUI gegengeprueft - bei Schneiderei kommt er
# nicht vor.
SOURCE_LABELS = {
    1: "Hergestellt",
    2: "Drop",
    4: "Quest",
    5: "Haendler",
    6: "Lehrer",
    16: "Geangelt",
    21: "Aus Taschendiebstahl",
}

# Der Code, auf dem der Trainer-Filter steht. Einmal benannt, damit weder Rechnung noch
# Ausgabetext die 6 noch einmal ausschreiben muessen.
TRAINER_CODE = 6

# Breite der Beschriftungen im Block unter jeder Tabelle.
LABEL_WIDTH = 32


def count_codes(entries: list[dict]) -> tuple[Counter, Counter, dict[int, list[str]]]:
    """Pro Code: Haeufigkeit, davon mit 'trainingcost', und bis zu drei Beispielnamen."""
    per_code = Counter()
    with_cost = Counter()
    examples = defaultdict(list)

    for entry in entries:
        for code in entry.get("source", []):
            per_code[code] += 1
            if "trainingcost" in entry:
                with_cost[code] += 1
            if len(examples[code]) < 3:
                examples[code].append(entry["name"])

    return per_code, with_cost, examples


def report_profession(profession: str, entries: list[dict]) -> Counter:
    """Gibt die Tabelle fuer einen Beruf aus und liefert die Zaehlung fuer die Uebersicht."""
    per_code, with_cost, examples = count_codes(entries)

    print(f"\n=== {profession}  ({len(entries)} Eintraege) ===")
    print(f"{'code':>4}  {'anzahl':>6}  {'mit cost':>8}  {'bedeutung':<22}  beispiele")
    for code, count in per_code.most_common():
        label = SOURCE_LABELS.get(code, "*** UNBEKANNT ***")
        names = ", ".join(examples[code])
        print(f"{code:>4}  {count:>6}  {with_cost[code]:>8}  {label:<22}  {names}")

    unknown = sorted(set(per_code) - set(SOURCE_LABELS))
    if unknown:
        print(f"!! Unbekannte Codes: {unknown} - in catalog_sources.md nachtragen")

    # Gegenprobe fuer den Trainer-Code: Die Korrelation mit 'trainingcost' muss in beide
    # Richtungen perfekt sein, sonst traegt der Trainer-Filter bei diesem Beruf nicht.
    cost_without_trainer = sum(
        1 for e in entries if "trainingcost" in e and TRAINER_CODE not in e.get("source", [])
    )
    missing = sum(1 for e in entries if "source" not in e)

    trainer_label = SOURCE_LABELS.get(TRAINER_CODE, "*** UNBEKANNT ***")
    rows = [
        (f"Eintraege mit Code {TRAINER_CODE} ({trainer_label})", str(per_code[TRAINER_CODE])),
        ("davon mit trainingcost", str(with_cost[TRAINER_CODE])),
        (
            f"trainingcost OHNE Code {TRAINER_CODE}",
            f"{cost_without_trainer}   (muss 0 sein)",
        ),
        ("ohne 'source'-Feld", f"{missing}  ({100 * missing / len(entries):.1f} %)"),
    ]
    for text, value in rows:
        print(f"  {text:<{LABEL_WIDTH}}: {value}")

    return per_code


def report_overview(per_profession: dict[str, Counter]) -> None:
    """
    Welcher Code taucht bei welchem Beruf auf?

    Das ist der eigentliche Grund fuer den Lauf ueber alle Berufe - in den Einzeltabellen
    darueber geht es zwischen sieben Ausgaben unter.
    """
    codes = sorted({code for counts in per_profession.values() for code in counts})
    width = max(len(name) for name in per_profession)

    print("\n\n=== Uebersicht: Code x Beruf ===")
    print(f"{'beruf':<{width}}  " + "  ".join(f"{code:>6}" for code in codes))
    for profession, counts in per_profession.items():
        # '.' statt 0: Der Unterschied zwischen "kommt nicht vor" und "kommt selten vor"
        # ist genau die Frage, um die es hier geht.
        cells = (f"{counts.get(code, '.'):>6}" for code in codes)
        print(f"{profession:<{width}}  " + "  ".join(cells))

    print()
    for code in codes:
        print(f"  {code:>4} = {SOURCE_LABELS.get(code, '*** UNBEKANNT ***')}")


def main() -> None:
    professions = {
        path.name.removesuffix(".de.json"): load(path.name)
        for path in sorted(PROBE_DIR.glob("*.de.json"))
    }
    if not professions:
        raise SystemExit(
            f"Keine *.de.json in {PROBE_DIR} - erst holen mit: uv run python tools/probe_all.py"
        )

    per_profession = {}
    for profession, entries in professions.items():
        if not entries:
            # Leere Datei nicht durchrutschen lassen: Sonst besteht jede Gegenprobe,
            # weil nichts da ist, was sie verletzen koennte.
            print(f"\n=== {profession}: leer - uebersprungen ===")
            continue
        per_profession[profession] = report_profession(profession, entries)

    if per_profession:
        report_overview(per_profession)


if __name__ == "__main__":
    main()
