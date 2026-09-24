"""
Was steckt in der Wowhead-Kategorie "Books"?

Der Plan vermutete einen Sammelposten, der Rezepte mehrerer Berufe enthaelt - dann
muesste die Kategorie mit in den Scope. Diese Auswertung soll das entscheiden.

Datei holen mit:
    uv run python tools/probe_listing.py \\
        --url https://www.wowhead.com/forever/de/items/recipes/books \\
        --var listviewitems --out data/probe/categories/books.de.json \\
        --html-out data/probe/categories/books.de.html

Die Kategorie liegt bewusst in einem Unterordner: Sie ist eine Item-Liste, kein
Berufs-Listing. Die Auswertungen hier globben data/probe/*.de.json nach Berufen ab
und wuerden sie sonst als weiteren Beruf mitzaehlen.
"""

import re
from collections import Counter

from _probe_data import PROBE_DIR, load, load_html

# Item-Klasse 9 ist "Rezept". Die Unterklasse sagt, zu welchem Beruf das Rezept
# gehoert; 0 ist die Sammelkategorie "Buch".
RECIPE_CLASS = 9
SUBCLASS_BOOK = 0

books = load("categories/books.de.json")


def main() -> None:
    print(f"Eintraege: {len(books)}")

    # 1. Hat der Kategorie-Slug ueberhaupt gefiltert? Bei 'tailoring-patterns' tat er
    #    es nicht (siehe catalog_sources.md Abschnitt 1) - das ist also keine
    #    Selbstverstaendlichkeit, sondern eine Pruefung.
    classes = Counter(e.get("classs") for e in books)
    subclasses = Counter(e.get("subclass") for e in books)
    print(f"classs   : {dict(classes)}")
    print(f"subclass : {dict(subclasses)}")

    fremd = [e for e in books if e.get("subclass") != SUBCLASS_BOOK]
    if fremd:
        print(f"\n!! {len(fremd)} Eintraege mit fremder Unterklasse - Slug filtert unsauber:")
        for entry in fremd[:10]:
            print(f"   {entry['id']:>8}  subclass={entry.get('subclass')}  {entry['name']}")

    # 2. Ist die Liste gekappt? Die Gesamtliste /items/recipes war es bei 1.000.
    html = load_html("categories/books.de.html")
    note = re.search(r'"note":\s*"([^"]*)"', html)
    print(f"\nnote: {note.group(1) if note else '(keine)'}")

    # 3. Klassen-Zauberbuecher tragen eine Klassenbeschraenkung, Berufsrezepte nicht.
    #    Die Eintraege ohne reqclass sind deshalb die einzigen Kandidaten fuer den Scope.
    ohne_reqclass = [e for e in books if "reqclass" not in e]
    print(f"\nmit reqclass (Klassenbuch)   : {len(books) - len(ohne_reqclass)}")
    print(f"ohne reqclass (zu pruefen)   : {len(ohne_reqclass)}")

    # 4. Die eigentliche Frage: Fehlt uns davon etwas? Ein Rezept-Item heisst nach dem
    #    Produkt, das es lehrt ("Bauplan: Felsgarten" -> Zauber "Felsgarten"). Wenn der
    #    Rest des Namens in einer unserer sieben Berufslisten steht, haben wir es schon.
    bekannt = {}
    for path in sorted(PROBE_DIR.glob("*.de.json")):
        profession = path.name.removesuffix(".de.json")
        for entry in load(path.name):
            bekannt.setdefault(entry["name"].casefold(), []).append(profession)

    print()
    for entry in ohne_reqclass:
        # Rezept-Items tragen einen Praefix wie "Bauplan: " oder "Rezept: ".
        produkt = entry["name"].split(": ", 1)[-1]
        treffer = bekannt.get(produkt.casefold())
        status = f"-> {', '.join(sorted(set(treffer)))}" if treffer else "-> NICHT im Scope"
        print(f"   {entry['id']:>8}  {entry['name']:<42} {status}")


if __name__ == "__main__":
    main()
