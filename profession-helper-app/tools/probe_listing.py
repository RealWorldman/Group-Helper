"""
M0-Spike: Laedt eine Wowhead-Listing-Seite und untersucht das eingebettete Listview-Datenarray.

Reine Aufklaerung - schreibt weder in die Datenbank noch in den Katalog.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import httpx

BASE_URL = "https://www.wowhead.com/forever"
USER_AGENT = "profession-helper-app/0.1 (privates Gilden-Tool; yves.etter18@gmail.com)"
TIMEOUT = 20.0

# Ein vollstaendiger JSON-String, inklusive escapter Anfuehrungszeichen.
STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
# Ein Schluessel ohne Anfuehrungszeichen, also `popularity:10` oder `{firstseenpatch: 0`.
UNQUOTED_KEY_RE = re.compile(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:")

# Datentypen im Block `WH.Gatherer.addData(<typ>, <locale>, {...})`.
GATHERER_ITEMS = 3  # Schluessel = item_id
GATHERER_SPELLS = 6  # Schluessel = spell_id


def fetch(url: str) -> str:
    """Laedt eine Seite. Ein Request, kein Retry - der Spike wird von Hand aufgerufen."""
    response = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def extract_balanced(text: str, open_pos: int) -> str:
    """
    Schneidet ab `text[open_pos]` (einer oeffnenden Klammer) bis zur passenden zu.

    Eine Regex reicht dafuer nicht: Der Inhalt enthaelt verschachtelte Klammern und
    Strings, die ihrerseits Klammern enthalten koennen. Deshalb wird die
    Schachtelungstiefe zeichenweise gezaehlt und Stringinhalt dabei uebersprungen.
    """
    depth = 0
    in_string = False
    escaped = False

    for pos in range(open_pos, len(text)):
        char = text[pos]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
            if depth == 0:
                return text[open_pos : pos + 1]

    raise ValueError(f"Die Klammer bei Position {open_pos} wird nie geschlossen")


def extract_listview(html: str, var_name: str) -> str:
    """Schneidet das JS-Array aus `var <var_name> = [...];` heraus."""
    marker = f"var {var_name} = ["
    start = html.find(marker)
    if start == -1:
        raise ValueError(f"'{marker}' kommt in der Seite nicht vor")

    return extract_balanced(html, start + len(marker) - 1)


def parse_loose(js_array: str) -> list[dict]:
    """
    Parst das Array, obwohl es kein gueltiges JSON ist.

    Wowhead mischt quoted und unquoted Schluessel (`"quality":1` neben
    `popularity:10`). Die Reparatur laeuft nur ausserhalb von Strings, damit ein
    Item namens `Ring, Gold: Klein` nicht versehentlich zerschnitten wird.
    Doppelte Schluessel gewinnt der letzte - das ist json-Standardverhalten und
    fuer die betroffenen Felder (quality) unkritisch.
    """
    repaired = []
    cursor = 0
    for match in STRING_RE.finditer(js_array):
        repaired.append(UNQUOTED_KEY_RE.sub(r'\1"\2":', js_array[cursor : match.start()]))
        repaired.append(match.group(0))
        cursor = match.end()
    repaired.append(UNQUOTED_KEY_RE.sub(r'\1"\2":', js_array[cursor:]))

    return json.loads("".join(repaired))


def extract_gatherer(html: str, data_type: int) -> dict:
    """
    Schneidet `WH.Gatherer.addData(<data_type>, <locale>, {...})` aus der Seite.

    Jede Listing-Seite traegt neben `listviewspells` zwei solche Bloecke:
    GATHERER_ITEMS liefert die Item-Stammdaten zu allen 'reagents' und 'creates',
    GATHERER_SPELLS die Zauberbeschreibung mit den Zahlenwerten.

    Anders als `listviewspells` ist der Block gueltiges JSON - alle Schluessel sind
    gequotet, `parse_loose` wird hier nicht gebraucht.
    """
    match = re.search(rf"WH\.Gatherer\.addData\({data_type},\s*\d+,\s*", html)
    if match is None:
        raise ValueError(f"Kein WH.Gatherer.addData({data_type}, ...) in der Seite")

    return json.loads(extract_balanced(html, html.index("{", match.end() - 1)))


def print_field_stats(entries: list[dict]) -> None:
    """Zeigt, welches Feld bei wie vielen Eintraegen ueberhaupt gesetzt ist."""
    counter = Counter()
    for entry in entries:
        counter.update(entry.keys())

    width = max(len(key) for key in counter)
    for key, count in counter.most_common():
        share = 100 * count / len(entries)
        print(f"  {key:<{width}}  {count:>5}  ({share:5.1f} %)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profession", default="tailoring", help="Berufs-Slug, z. B. tailoring")
    parser.add_argument("--locale", default="", help="Sprach-Segment der URL, z. B. de (leer = en)")
    parser.add_argument("--var", default="listviewspells", help="Name der JS-Variablen")
    parser.add_argument("--out", type=Path, help="Roh-Eintraege zusaetzlich als JSON ablegen")
    args = parser.parse_args()

    # Ohne Sprach-Segment liefert Wowhead Englisch: /forever/spells/... statt /forever/de/spells/...
    locale_segment = f"/{args.locale}" if args.locale else ""
    url = f"{BASE_URL}{locale_segment}/spells/professions/{args.profession}"
    print(f"GET {url}")
    html = fetch(url)
    print(f"  {len(html)} Zeichen empfangen")

    entries = parse_loose(extract_listview(html, args.var))
    print(f"  {len(entries)} Eintraege geparst")
    if not entries:
        print("Leeres Array - Slug falsch oder Seite umgebaut?")
        return 1

    print("\nFeld-Abdeckung:")
    print_field_stats(entries)

    print("\nErster Eintrag:")
    print(json.dumps(entries[0], indent=2, ensure_ascii=False))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nGeschrieben: {args.out}")
    else:
        # Ohne --out bleibt nichts liegen. Die Skripte in tools/analysis/ brauchen die Datei.
        suffix = f".{args.locale}" if args.locale else ""
        print(
            f"\nNichts gespeichert. Mit --out data/probe/{args.profession}{suffix}.json "
            f"landet der Datensatz auf der Platte."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
