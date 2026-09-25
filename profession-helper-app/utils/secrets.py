"""
Zugriff auf die gemeinsame secrets.json.

Die Datei gehoert beiden Bots und sieht so aus:

    {
      "DISCORD":     [{"AppName": "...", "DiscordToken": "..."}, ...],
      "RAID-HELPER": [{"ServerID": "...", "ApiKey": "..."}, ...]
    }

Im Original (group-helper-app/utils/secrets.py) steht dieselbe Suche dreimal:
Datei laden, Liste unter einem Abschnitt durchgehen, ein Feld vergleichen, ein
anderes zurueckgeben. Hier steht sie einmal in `get_secret()`, und die
benannten Funktionen sind duenne Huellen darum.

Zwei weitere Unterschiede zum Original:

* **Die Datei wird einmal gelesen und gemerkt.** Das Original liest sie bei
  jedem Zugriff neu und schreibt dabei jedes Mal eine INFO-Zeile ins Log.
* **`require_secret()` wirft**, statt None zurueckzugeben. Ein fehlender
  Bot-Token soll den Start mit einer klaren Meldung abbrechen, nicht als
  `None` bis in den Discord-Client durchgereicht werden.
"""

import json
import logging
from pathlib import Path
from typing import Any

import config

log = logging.getLogger(__name__)

# Pfad -> Inhalt. Die Datei aendert sich im Betrieb nicht.
_cache: dict[Path, dict[str, Any]] = {}


def load_secrets(pfad: Path | None = None) -> dict[str, Any]:
    """
    Laedt die Secrets-Datei, beim zweiten Aufruf aus dem Zwischenspeicher.

    Wirft nicht: Eine fehlende oder kaputte Datei wird geloggt und als leeres
    Dict behandelt. Was daraus folgt, entscheidet der Aufrufer - fuer den
    Bot-Token ist das `require_secret()`, fuer Optionales `get_secret()`.
    """
    pfad = pfad or config.SECRETS_FILE
    if pfad in _cache:
        return _cache[pfad]

    if not pfad.exists():
        log.error("Secrets-Datei nicht gefunden: %s", pfad)
        return {}

    try:
        inhalt = json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as fehler:
        # Bewusst nur JSONDecodeError statt eines pauschalen `except Exception`:
        # Ein Rechtefehler oder ein kaputter Datentraeger soll durchschlagen und
        # nicht als "keine Secrets" erscheinen.
        log.error("Secrets-Datei ist kein gueltiges JSON (%s): %s", pfad, fehler)
        return {}

    _cache[pfad] = inhalt
    log.info("Secrets geladen aus %s", pfad)
    return inhalt


def get_secret(
    section: str,
    match_field: str,
    match_value: str,
    value_field: str,
    pfad: Path | None = None,
) -> str | None:
    """
    Sucht in `section` den Eintrag, dessen `match_field` zu `match_value` passt,
    und gibt dessen `value_field` zurueck.

    Der Vergleich laeuft ueber `str()`: In der Datei stehen Discord-IDs mal als
    Zahl, mal als Zeichenkette, und `123 != "123"` waere ein Fehlschlag, den
    niemand im JSON sieht.

    **Der Wert wird nie geloggt** - nur, ob und wo gesucht wurde.
    """
    eintraege = load_secrets(pfad).get(section, [])
    for eintrag in eintraege:
        if str(eintrag.get(match_field)) == str(match_value):
            wert = eintrag.get(value_field)
            if wert:
                log.info("%s gefunden: %s=%s", value_field, match_field, match_value)
                return wert
            log.warning(
                "Eintrag %s=%s gefunden, aber ohne '%s'", match_field, match_value, value_field
            )
            return None

    log.warning("Kein Eintrag in '%s' mit %s=%s", section, match_field, match_value)
    return None


def require_secret(
    section: str,
    match_field: str,
    match_value: str,
    value_field: str,
    pfad: Path | None = None,
) -> str:
    """Wie `get_secret()`, bricht aber mit einer verwertbaren Meldung ab."""
    wert = get_secret(section, match_field, match_value, value_field, pfad)
    if wert is None:
        raise RuntimeError(
            f"'{value_field}' fehlt: kein Eintrag in '{section}' mit "
            f"{match_field}={match_value} in {pfad or config.SECRETS_FILE}"
        )
    return wert


def get_discord_token(app_name: str | None = None, pfad: Path | None = None) -> str:
    """Der Bot-Token dieser Anwendung. Fehlt er, startet der Bot nicht."""
    return require_secret(
        "DISCORD", "AppName", app_name or config.DISCORD_APP_NAME, "DiscordToken", pfad
    )


def clear_cache() -> None:
    """Verwirft den Zwischenspeicher. Fuer Tests."""
    _cache.clear()
