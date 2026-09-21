"""
Wem fehlt das Feld 'creates', und warum?

Ergebnis (Schneiderei): 80 Eintraege ohne 'creates'. 8 davon sind Berufsraenge, die
uebrigen 72 sind echte Rezepte, bei denen Wowhead die Item-Verknuepfung noch nicht
nachgetragen hat - fast alle im neuen Forever-ID-Bereich.
"""

from _probe_data import is_forever, load, recipes_only

entries = load("tailoring.de.json")
recipes = recipes_only(entries)

print(f"Eintraege gesamt : {len(entries)}")
print(f"davon Berufsraenge: {len(entries) - len(recipes)}")
print(f"echte Rezepte    : {len(recipes)}\n")

with_creates = [e for e in recipes if "creates" in e]
without = [e for e in recipes if "creates" not in e]
print(f"mit 'creates': {len(with_creates)}   ohne: {len(without)}\n")

# Verdacht: die Luecken haengen am Alter des Zaubers.
print(f"{'gruppe':<14} {'n':>4}  {'davon Forever (id >= 400k)':>28}")
for label, group in (("mit creates", with_creates), ("ohne creates", without)):
    forever = sum(1 for e in group if is_forever(e))
    share = 100 * forever / len(group)
    print(f"{label:<14} {len(group):>4}  {forever:>15} / {len(group):<4} ({share:4.1f} %)")

# Bleibt der Produktname trotzdem stehen? Davon haengt die Wollstofftaschen-Frage ab.
named = sum(1 for e in without if e.get("name"))
print(f"\nohne 'creates', aber mit gefuelltem 'name': {named} / {len(without)}")

print("\n10 Beispiele:")
for entry in without[:10]:
    print(f"  id={entry['id']:<8} learnedat={entry.get('learnedat'):<4} {entry['name']}")
