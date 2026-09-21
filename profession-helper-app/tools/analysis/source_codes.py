"""
Was bedeuten die Zahlen im Feld 'source'?

Die Bedeutungen sind gegen die Trefferzahlen der Wowhead-Filter belegt (21.09.2026),
siehe tools/catalog_sources.md Abschnitt 3. Taucht bei einem anderen Beruf ein Code
auf, der hier nicht steht, meldet dieses Skript ihn als UNBEKANNT.
"""

from collections import Counter, defaultdict

from _probe_data import load

# Belegt durch Abgleich mit /forever/de/skill=197/schneiderei#recipes;source=<Quelle>
SOURCE_LABELS = {
    2: "Drop",
    4: "Quest",
    5: "Haendler",
    6: "Lehrer",
    16: "Geangelt",
    21: "Aus Taschendiebstahl",
}

entries = load("tailoring.de.json")

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

print(f"{'code':>4}  {'anzahl':>6}  {'mit cost':>8}  {'bedeutung':<22}  beispiele")
for code, count in per_code.most_common():
    label = SOURCE_LABELS.get(code, "*** UNBEKANNT ***")
    print(f"{code:>4}  {count:>6}  {with_cost[code]:>8}  {label:<22}  {', '.join(examples[code])}")

unknown = set(per_code) - set(SOURCE_LABELS)
if unknown:
    print(f"\n!! Unbekannte Codes: {sorted(unknown)} - in catalog_sources.md nachtragen")

# Gegenprobe fuer 'Code 6 == Lehrer': die Korrelation mit trainingcost muss in beide
# Richtungen perfekt sein, sonst traegt der Trainer-Filter nicht.
cost_without_6 = sum(1 for e in entries if "trainingcost" in e and 6 not in e.get("source", []))
code6 = per_code[6]
print("\nCode 6 = Lehrer:")
print(f"  Eintraege mit Code 6              : {code6}")
print(f"  davon mit trainingcost            : {with_cost[6]}")
print(f"  trainingcost OHNE Code 6          : {cost_without_6}   (muss 0 sein)")

missing = sum(1 for e in entries if "source" not in e)
print(f"\nohne 'source'-Feld: {missing} / {len(entries)} ({100 * missing / len(entries):.1f} %)")
