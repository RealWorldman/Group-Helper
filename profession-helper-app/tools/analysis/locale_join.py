"""
Join EN/DE ueber die spell_id: wie viel ist wirklich uebersetzt?

Das entscheidet, ob der EN-Fallback der Normalfall ist oder nur ein Sicherungsnetz -
und ob die Zweisprachigkeit aus dem Plan auf beiden Beinen steht.
"""

from _probe_data import is_forever, load

en = {e["id"]: e for e in load("tailoring.json")}
de = {e["id"]: e for e in load("tailoring.de.json")}

print(f"EN: {len(en)}   DE: {len(de)}")
print(f"nur EN: {len(en.keys() - de.keys())}   nur DE: {len(de.keys() - en.keys())}")

shared = en.keys() & de.keys()
translated = [i for i in shared if en[i]["name"] != de[i]["name"]]
same = [i for i in shared if en[i]["name"] == de[i]["name"]]

print(f"\nuebersetzt (Name weicht ab): {len(translated)} / {len(shared)}")
print(f"identisch (noch englisch?) : {len(same)}")

print("\n10 uebersetzte Beispiele:")
for i in sorted(translated)[:10]:
    print(f"  {i:>8}  {en[i]['name']:<38} -> {de[i]['name']}")

if same:
    print("\n10 identisch gebliebene:")
    for i in sorted(same)[:10]:
        print(f"  {i:>8}  {en[i]['name']}")

# Haengt die Uebersetzung am Alter des Zaubers? Bei den neuen Forever-Rezepten waere
# eine Luecke am ehesten zu erwarten.
print()
for label, group in (
    ("Classic (id < 400k)", [i for i in shared if not is_forever(en[i])]),
    ("Forever (id >= 400k)", [i for i in shared if is_forever(en[i])]),
):
    hit = sum(1 for i in group if en[i]["name"] != de[i]["name"])
    print(f"{label:<22} uebersetzt: {hit}/{len(group)}")
