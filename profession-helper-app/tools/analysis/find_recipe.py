"""
Sucht Rezepte nach Namensteil - die Handprobe fuer konkrete Gildenfragen.

    uv run python tools/analysis/find_recipe.py woll
    uv run python tools/analysis/find_recipe.py bag --file tailoring.json

Sucht in DE und EN gleichzeitig, wenn beide Dateien vorhanden sind. Das ist die
Zweisprachigkeit aus dem Plan im Kleinen: eine Eingabe, beide Sprachen treffen.
"""

import argparse
import sys

from _probe_data import load


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("term", help="Namensteil, Gross-/Kleinschreibung egal")
    parser.add_argument("--full", action="store_true", help="ganze Eintraege ausgeben")
    args = parser.parse_args()

    needle = args.term.casefold()
    de = load("tailoring.de.json")
    en = {e["id"]: e for e in load("tailoring.json")}

    def matches(entry: dict) -> bool:
        """Treffer, wenn der Suchbegriff im deutschen ODER im englischen Namen steckt."""
        return needle in entry["name"].casefold() or needle in en[entry["id"]]["name"].casefold()

    hits = [e for e in de if matches(e)]

    if not hits:
        print(f"keine Treffer fuer {args.term!r}")
        return 1

    print(f"{len(hits)} Treffer fuer {args.term!r}:\n")
    for entry in sorted(hits, key=lambda e: e["name"]):
        creates = entry.get("creates")
        item = creates[0] if creates else "-"
        print(
            f"  spell={entry['id']:<8} item={str(item):<8} skill={entry.get('learnedat'):<4} "
            f"{entry['name']}  /  {en[entry['id']]['name']}"
        )
        if args.full:
            print(f"      {entry}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
