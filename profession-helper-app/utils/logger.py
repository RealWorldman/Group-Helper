"""
Logging-Einrichtung.

Uebernommen aus group-helper-app/utils/logger.py, mit drei Aenderungen:

* **Das Verzeichnis kommt aus `config.LOG_DIR`**, nicht als hartkodiertes
  `'logs/'`. Das Original legt das Verzeichnis relativ zum Arbeitsverzeichnis an;
  unter systemd ist das nicht das Projektverzeichnis, und die Logs landen
  irgendwo.
* **Mehrfachaufruf ist harmlos.** Das Original haengt bei jedem Aufruf neue
  Handler an die Wurzel - jede Zeile erscheint dann doppelt, dreifach, ...
  Beim Bot faellt das nicht auf (ein Aufruf beim Start), in Tests und Skripten
  schon.
* **discord.py wird gedaempft.** Die Bibliothek loggt auf INFO jeden Gateway-Herzschlag;
  in einer Datei mit 30 Tagen Aufbewahrung ist das nur Rauschen.
"""

import logging
from logging.handlers import TimedRotatingFileHandler

import config

# Datei- und Zeilennummer sind beim Debuggen den Platz wert.
FORMAT = "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

# Kennzeichen an unseren Handlern, um sie bei einem zweiten Aufruf wiederzuerkennen.
_MARKER = "profession-helper"


def _handler_schon_da() -> bool:
    return any(getattr(h, "_marker", None) == _MARKER for h in logging.getLogger().handlers)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Richtet Datei- und Konsolen-Logging ein. Ein zweiter Aufruf tut nichts.

    Zwei Dateien: `bot.log` bekommt alles, `errors.log` nur Fehler. Die Trennung
    spart beim Debuggen das Suchen - man schaut zuerst in die kurze Datei.
    """
    if _handler_schon_da():
        return

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(FORMAT)

    handlers: list[logging.Handler] = []
    for dateiname, handler_level in (("bot.log", level), ("errors.log", logging.ERROR)):
        handler = TimedRotatingFileHandler(
            filename=config.LOG_DIR / dateiname,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        handler.setLevel(handler_level)
        handlers.append(handler)

    # Unter systemd landet die Konsole im Journal. Das ist gewollt: `journalctl -u`
    # zeigt dann dasselbe wie die Datei, ohne sich einloggen und blaettern zu muessen.
    konsole = logging.StreamHandler()
    konsole.setLevel(level)
    handlers.append(konsole)

    wurzel = logging.getLogger()
    wurzel.setLevel(level)
    for handler in handlers:
        handler.setFormatter(formatter)
        handler._marker = _MARKER  # noqa: SLF001 - eigenes Attribut, kein fremdes
        wurzel.addHandler(handler)

    # Nicht ausschalten, nur daempfen: Eine Warnung von discord.py wollen wir sehen.
    logging.getLogger("discord").setLevel(logging.WARNING)

    logging.info("Logging eingerichtet, Verzeichnis: %s", config.LOG_DIR)
