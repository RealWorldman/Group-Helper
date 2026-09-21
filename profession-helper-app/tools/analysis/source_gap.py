"""
Haengt die fehlende Quellenangabe am Alter des Zaubers?

Davon haengt ab, wie brauchbar der Trainer-Filter heute ist - und ob er sich bis zum
Release durch Wowheads Crowdsourcing von selbst verbessert.
"""

from _probe_data import is_forever, load, recipes_only

recipes = recipes_only(load("tailoring.de.json"))
print(f"echte Rezepte (ohne Berufsraenge): {len(recipes)}\n")

print(f"{'gruppe':<22} {'n':>4}  {'ohne source':>18}  {'Lehrer (Code 6)':>16}")
for label, group in (
    ("Classic (id < 400k)", [e for e in recipes if not is_forever(e)]),
    ("Forever (id >= 400k)", [e for e in recipes if is_forever(e)]),
):
    missing = sum(1 for e in group if "source" not in e)
    trainer = sum(1 for e in group if 6 in e.get("source", []))
    share = 100 * missing / len(group)
    print(f"{label:<22} {len(group):>4}  {missing:>9} ({share:5.1f} %)  {trainer:>16}")

print(
    "\nLies das nicht als Aussage ueber Forever: die wenigen Lehrer-Treffer im neuen\n"
    "ID-Bereich sind mit hoher Wahrscheinlichkeit fehlende Daten, keine Design-Entscheidung."
)
