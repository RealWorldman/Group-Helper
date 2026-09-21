"""
Prueft parse_loose() und extract_listview() gegen die vier bekannten Grenzfaelle.

Laeuft ohne Netz und ohne Rohdaten. In M1 sollte daraus ein echter pytest-Fall werden.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from probe_listing import extract_listview, parse_loose  # noqa: E402

CASES = [
    (
        "unquoted Keys neben quoted Keys",
        '[{"id":1,popularity:10,firstseenpatch: 0}]',
        [{"id": 1, "popularity": 10, "firstseenpatch": 0}],
    ),
    (
        "Komma und Doppelpunkt INNERHALB eines Strings",
        '[{"name":"Ring, Gold: Klein",quality:2}]',
        [{"name": "Ring, Gold: Klein", "quality": 2}],
    ),
    (
        "escaptes Anfuehrungszeichen im String",
        '[{"name":"Khadgar\\"s Unlocking",popularity:3}]',
        [{"name": 'Khadgar"s Unlocking', "popularity": 3}],
    ),
]


def main() -> int:
    failures = 0

    for label, raw, expected in CASES:
        actual = parse_loose(raw)
        ok = actual == expected
        failures += not ok
        print(f"[{'ok ' if ok else 'FEHL'}] {label}")
        if not ok:
            print(f"       erwartet: {expected}")
            print(f"       erhalten: {actual}")

    # Vierter Fall: eine Klammer im Namen darf die Tiefenzaehlung nicht stoeren.
    html = 'davor var listviewspells = [{"name":"Trank [gross]","creates":[123,1,1]}]; danach'
    actual = parse_loose(extract_listview(html, "listviewspells"))
    expected = [{"name": "Trank [gross]", "creates": [123, 1, 1]}]
    ok = actual == expected
    failures += not ok
    print(f"[{'ok ' if ok else 'FEHL'}] Klammer im String, aus HTML geschnitten")
    if not ok:
        print(f"       erwartet: {expected}")
        print(f"       erhalten: {actual}")

    print(f"\n{len(CASES) + 1 - failures}/{len(CASES) + 1} bestanden")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
