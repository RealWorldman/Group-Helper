"""
Holt die Listings aller Berufe in beiden Sprachen - ein Lauf statt zwoelf Aufrufen.

Ergaenzt tools/probe_listing.py um die Liste der Berufe, das Rate-Limit von 1 req/s
und einen HTML-Cache. Laden und Parsen selbst kommt unveraendert von dort.

Pro Beruf und Sprache entstehen drei Dateien - eine je Datenblock der Seite:

    tailoring.de.json          var listviewspells   (Rezepte)
    tailoring.de.spells.json   addData(6, ...)      (Beschreibung, Icon, Rang)
    tailoring.de.items.json    addData(3, ...)      (Name, Qualitaet, Icon je Item)

Die Bloecke werden bewusst nicht ins Listing gemischt: So bleibt jede Datei eine
originalgetreue Kopie genau eines Blocks, und die Gegenprobe "neu geholt ergibt
byteweise dasselbe" bleibt moeglich.

Der HTML-Cache entscheidet, ob ein Request noetig ist: Liegt data/probe/<slug>.html
schon da, wird nichts geholt. Ein zweiter Lauf nach einem korrigierten Slug kostet
deshalb nur die Seiten, die wirklich fehlen.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from probe_listing import (
    BASE_URL,
    GATHERER_ITEMS,
    GATHERER_SPELLS,
    extract_gatherer,
    extract_listview,
    fetch,
    parse_loose,
)

# __file__ = tools/probe_all.py  ->  parents[1] = profession-helper-app/
PROBE_DIR = Path(__file__).resolve().parents[1] / "data" / "probe"

# Die sieben Berufe im Scope (PLAN.md). 'tailoring' ist als Slug belegt, 'enchanting'
# hat auf Deutsch funktioniert - die uebrigen fuenf sind geraten und genau das, was
# dieser Lauf klaeren soll.
PROFESSIONS = [
    "alchemy",
    "blacksmithing",
    "enchanting",
    "engineering",
    "leatherworking",
    "mining",
    "tailoring",
]

# Leerer String = Englisch: /forever/spells/... statt /forever/de/spells/...
LOCALES = ["", "de"]

VAR_NAME = "listviewspells"
RATE_LIMIT_SECONDS = 1.0

# Die beiden Gatherer-Bloecke derselben Seite, je mit der Endung ihrer Datei.
GATHERER_BLOCKS = (
    (".spells.json", GATHERER_SPELLS),
    (".items.json", GATHERER_ITEMS),
)


def probe_path(slug: str, locale: str, suffix: str) -> Path:
    """data/probe/tailoring.de.json bzw. tailoring.html - Locale nur, wenn gesetzt."""
    locale_part = f".{locale}" if locale else ""
    return PROBE_DIR / f"{slug}{locale_part}{suffix}"


def write_json(path: Path, data: Any) -> None:
    """Schreibt eingerueckt und mit echten Umlauten - die Dateien werden gelesen."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def listing_url(slug: str, locale: str) -> str:
    locale_segment = f"/{locale}" if locale else ""
    return f"{BASE_URL}{locale_segment}/spells/professions/{slug}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refetch",
        action="store_true",
        help="HTML-Cache ignorieren und alle Seiten neu holen",
    )
    args = parser.parse_args()

    PROBE_DIR.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, str, list[dict]]] = []
    failures: list[tuple[str, str, str]] = []
    # Die Pause gehoert vor den *naechsten* Request, nicht hinter den letzten - und
    # nur, wenn wirklich einer gelaufen ist. Cache-Treffer warten nicht.
    fetched_before = False

    for slug in PROFESSIONS:
        for locale in LOCALES:
            label = f"{slug}{'.' + locale if locale else ''}"
            html_file = probe_path(slug, locale, ".html")

            if html_file.exists() and not args.refetch:
                html = html_file.read_text(encoding="utf-8")
                print(f"[cache] {label:<22} {len(html):>8} Zeichen")
            else:
                if fetched_before:
                    time.sleep(RATE_LIMIT_SECONDS)
                url = listing_url(slug, locale)
                print(f"[GET]   {label:<22} {url}")
                fetched_before = True
                try:
                    html = fetch(url)
                except httpx.HTTPError as exc:
                    print(f"        !! Request fehlgeschlagen: {exc}")
                    failures.append((slug, locale, f"Request: {exc}"))
                    continue
                html_file.write_text(html, encoding="utf-8")

            try:
                entries = parse_loose(extract_listview(html, VAR_NAME))
            except ValueError as exc:
                # Kein Listview in der Seite: falscher Slug oder Seite umgebaut.
                print(f"        !! Kein Datenarray: {exc}")
                failures.append((slug, locale, f"Parsing: {exc}"))
                continue

            if not entries:
                print("        !! Leeres Array")
                failures.append((slug, locale, "leeres Array"))
                continue

            write_json(probe_path(slug, locale, ".json"), entries)

            blocks = {}
            for suffix, data_type in GATHERER_BLOCKS:
                try:
                    block = extract_gatherer(html, data_type)
                except ValueError as exc:
                    # Listing gerettet, Block fehlt: Das ist ein Teilausfall, kein
                    # Grund, die schon geschriebene Rezeptliste zu verwerfen.
                    print(f"        !! {suffix}: {exc}")
                    failures.append((slug, locale, f"{suffix}: {exc}"))
                    continue
                write_json(probe_path(slug, locale, suffix), block)
                blocks[suffix] = block

            results.append((slug, locale, entries, blocks))

    report(results, failures)
    return 1 if failures else 0


def report(
    results: list[tuple[str, str, list[dict], dict[str, dict]]],
    failures: list[tuple[str, str, str]],
) -> None:
    """Ueberblick pro Beruf: reicht, um Slug und Datenqualitaet sofort zu beurteilen."""
    header = f"{'beruf':<22} {'n':>5} {'zauber':>7} {'items':>6}  {'skill':<14} source-codes"
    print(f"\n{header}")
    for slug, locale, entries, blocks in results:
        label = f"{slug}{'.' + locale if locale else ''}"
        # Ein Rezept kann zu mehreren Berufen gehoeren (Schneiderei hat einen Eintrag
        # mit skill [165, 197]), deshalb flach einsammeln statt pro Eintrag zaehlen.
        skills = sorted({s for e in entries for s in e.get("skill", [])})
        sources = sorted({s for e in entries for s in e.get("source", [])})
        # '-' statt 0, damit ein fehlender Block nicht wie ein leerer aussieht.
        counts = [
            str(len(blocks[suffix])) if suffix in blocks else "-"
            for suffix, _ in GATHERER_BLOCKS
        ]
        print(
            f"{label:<22} {len(entries):>5} {counts[0]:>7} {counts[1]:>6}  "
            f"{str(skills):<14} {sources}"
        )

    if failures:
        print(f"\n{len(failures)} Fehlschlaege - Slug pruefen und erneut laufen lassen:")
        for slug, locale, reason in failures:
            label = f"{slug}{'.' + locale if locale else ''}"
            print(f"  {label:<22}  {reason}")
    else:
        print("\nAlle Berufe geladen.")


if __name__ == "__main__":
    sys.exit(main())
