"""
Tests fuer utils/textnorm.py.

Die Faelle sind keine erfundenen Beispiele: Bis auf die Tastatur-Varianten stammen
alle Namen aus den Probe-Daten unter data/probe/ und aus den Parsing-Fallen, die
in tools/catalog_sources.md Abschnitt 2 dokumentiert sind.
"""

import pytest

from utils.textnorm import normalize, normalize_compact


@pytest.mark.parametrize(
    ("roh", "erwartet"),
    [
        # Der Normalfall: Kleinschreibung, sonst nichts zu tun.
        ("Leinenstiefel", "leinenstiefel"),
        ("Brown Linen Vest", "brown linen vest"),
        # Umlaute werden ausgeschrieben ...
        ("Gewächshaus", "gewaechshaus"),
        ("Räucherkerze", "raeucherkerze"),
        ("Kürschnerei", "kuerschnerei"),
        # ... und zwar so, dass die Tastatur-Variante dasselbe ergibt. Das ist der
        # eigentliche Zweck der Ersetzung.
        ("Gewaechshaus", "gewaechshaus"),
        ("Raeucherkerze", "raeucherkerze"),
        # 'ß' erledigt casefold(), nicht die Umlaut-Tabelle.
        ("Geschmolzene Gießerei", "geschmolzene giesserei"),
        ("Grosse Beweglichkeit", "grosse beweglichkeit"),
        ("Große Beweglichkeit", "grosse beweglichkeit"),
        # Satzzeichen trennen, statt zu verschwinden.
        ("Ring, Gold: Klein", "ring gold klein"),
        ("Khadgar's Unlocking", "khadgar s unlocking"),
        ("Armschiene - Schwache Beweglichkeit", "armschiene schwache beweglichkeit"),
        ("Trank [gross]", "trank gross"),
        # Akzente ausserhalb des Deutschen fallen weg.
        ("Café Crème", "cafe creme"),
        # Raender und Mehrfach-Leerzeichen.
        ("  Doppelter   Abstand  ", "doppelter abstand"),
        ("", ""),
        ("---", ""),
    ],
)
def test_normalize(roh: str, erwartet: str) -> None:
    assert normalize(roh) == erwartet


def test_normalize_ist_idempotent() -> None:
    """Ein zweiter Durchlauf darf nichts mehr aendern - sonst haengt das Ergebnis
    davon ab, wie oft normalisiert wurde."""
    for roh in ("Gewächshaus", "Ring, Gold: Klein", "Große Beweglichkeit"):
        einmal = normalize(roh)
        assert normalize(einmal) == einmal


@pytest.mark.parametrize(
    ("roh", "erwartet"),
    [
        ("Wollstofftasche", "wollstofftasche"),
        ("Wollstoff-Tasche", "wollstofftasche"),
        ("Wollstoff Tasche", "wollstofftasche"),
        ("Gewächshaus", "gewaechshaus"),
    ],
)
def test_normalize_compact(roh: str, erwartet: str) -> None:
    assert normalize_compact(roh) == erwartet


def test_umlaut_vor_akzent_zerlegung() -> None:
    """
    Die Regressionsprobe fuer die Reihenfolge der Schritte in normalize().

    Wuerde NFKD vor der Umlaut-Ersetzung laufen, kaeme "gewachshaus" heraus - und
    der Fehler faende sich erst, wenn eine Gildensuche ins Leere laeuft.
    """
    assert normalize("Gewächshaus") == "gewaechshaus"
    assert normalize("Gewächshaus") != "gewachshaus"
