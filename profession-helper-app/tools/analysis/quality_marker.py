"""
Ist 'quality == -1' ein verlaesslicher Marker fuer 'kein verknuepftes Item'?

Wenn ja, kann der Katalog-Import diese Rezepte kennzeichnen ("Produkt bekannt,
Item-Link fehlt noch") und beim naechsten Update automatisch nachziehen.

Zusaetzlich: mehrfach belegte Namen, die der Resolver in M3 aufloesen muss.
"""

from collections import Counter

from _probe_data import load

entries = load("tailoring.de.json")

no_creates_minus1 = sum(1 for e in entries if "creates" not in e and e.get("quality") == -1)
no_creates_total = sum(1 for e in entries if "creates" not in e)
has_creates_minus1 = sum(1 for e in entries if "creates" in e and e.get("quality") == -1)

print("quality == -1 als Marker fuer fehlendes 'creates':")
print(f"  ohne creates und quality == -1: {no_creates_minus1} / {no_creates_total}  (Treffer)")
print(f"  MIT  creates und quality == -1: {has_creates_minus1}            (Fehltreffer)")
reliable = has_creates_minus1 == 0 and no_creates_minus1 == no_creates_total
print(f"  -> {'verlaesslich' if reliable else 'NICHT verlaesslich'}")

names = Counter(e["name"] for e in entries)
dupes = {name: count for name, count in names.items() if count > 1}
print(f"\nmehrfach belegte Namen: {len(dupes)}")
for name, count in sorted(dupes.items(), key=lambda kv: -kv[1])[:8]:
    print(f"  {count}x  {name}")

# Klassischer Fall: Classic-Version und ueberarbeitete Forever-Version tragen denselben Namen.
print("\nBeispiel 'Bodenlose Tasche' / 'Bottomless Bag':")
for entry in entries:
    if entry["name"] == "Bodenlose Tasche":
        print(f"  {entry['id']:>8}  creates={entry.get('creates')}  {entry['name']}")
