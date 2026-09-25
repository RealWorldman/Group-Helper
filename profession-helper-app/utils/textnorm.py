"""
Normalisierung von Namen fuer Suche und Vergleich.

Jede `*_norm`-Spalte im Datenmodell entsteht hier, und der Resolver vergleicht
ausschliesslich normalisierte Formen. Die Funktion ist damit die Stelle, an der
entschieden wird, was als "derselbe Name" gilt - und sie muss fuer Deutsch und
Englisch gleichzeitig funktionieren.

Beispiele:
    "Gewaechshaus"                 -> "gewaechshaus"
    "Gewaechshaus" (mit Umlaut)    -> "gewaechshaus"
    "Ring, Gold: Klein"            -> "ring gold klein"
    "Khadgar's Unlocking"          -> "khadgar s unlocking"
"""

import re
import unicodedata

# Deutsche Umlaute werden ausgeschrieben, nicht entschaerft.
#
# Der Unterschied entscheidet ueber Treffer oder Fehlschlag: Wer auf einer
# Tastatur ohne Umlaute "Gewaechshaus" tippt, muss dasselbe Ergebnis bekommen wie
# bei "Gewächshaus". Ein blosses Entfernen der Diakritika (wie es SQLites
# `remove_diacritics 2` tut) ergaebe "gewachshaus" und wuerde die getippte
# Variante verfehlen.
#
# 'ß' fehlt hier absichtlich: `str.casefold()` macht daraus bereits "ss", und die
# Ersetzung laeuft nach dem Casefold.
UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue"})

# Alles, was kein Buchstabe und keine Ziffer ist, trennt Woerter. Apostroph und
# Doppelpunkt aus Item-Namen werden damit zu Leerzeichen, nicht zu nichts:
# "Khadgar's" wird zu "khadgar s" und bleibt in Teilen suchbar.
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    """
    Bringt einen Namen auf die Form, in der verglichen und gesucht wird.

    Die Reihenfolge der Schritte ist nicht beliebig:

    1. `casefold()` statt `lower()` - es behandelt Sonderfaelle wie 'ß' -> "ss".
    2. Umlaute ausschreiben. **Muss vor Schritt 3 stehen.** Danach waere 'ä' in
       'a' + kombinierendes Trema zerlegt, das Trema wuerde entfernt und aus
       "Gewächshaus" wuerde "gewachshaus" statt "gewaechshaus".
    3. NFKD zerlegen und kombinierende Zeichen wegwerfen - entfernt Akzente aus
       franzoesischen oder spanischen Item-Namen, die nach Schritt 2 noch da sind.
    4. Alles Uebrige, was kein a-z0-9 ist, zu einem Leerzeichen.
    5. Mehrfache Leerzeichen zusammenziehen, Raender abschneiden.
    """
    folded = text.casefold().translate(UMLAUTS)
    decomposed = unicodedata.normalize("NFKD", folded)
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return NON_ALNUM_RE.sub(" ", without_marks).strip()


def normalize_compact(text: str) -> str:
    """
    Wie `normalize()`, aber ohne Leerzeichen.

    Fuer Komposita gedacht: "Wollstoff-Tasche", "Wollstoff Tasche" und
    "Wollstofftasche" ergeben dieselbe kompakte Form. Der Resolver nutzt das als
    zweite Stufe, wenn der normale Vergleich nichts findet - **nicht** als Ersatz,
    denn ohne Wortgrenzen liefert eine Teilstringsuche schnell Unsinn.
    """
    return normalize(text).replace(" ", "")
