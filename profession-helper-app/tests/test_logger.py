"""
Tests fuer utils/logger.py.

Geprueft wird nur das, was gegenueber der Vorlage aus group-helper-app neu ist:
das Verzeichnis aus der Konfiguration und der harmlose Mehrfachaufruf.
"""

import logging

import pytest

import config
from utils import logger


@pytest.fixture
def eigenes_log_verzeichnis(tmp_path, monkeypatch):
    """
    Schiebt die Logs in ein Wegwerf-Verzeichnis und raeumt die Wurzel hinterher auf.

    Ohne das Aufraeumen schriebe jeder folgende Test in dieselben Handler - und
    pytest faenge die Ausgabe nicht mehr richtig ein.
    """
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    wurzel = logging.getLogger()
    vorher = list(wurzel.handlers)
    yield tmp_path / "logs"
    for handler in wurzel.handlers:
        if handler not in vorher:
            handler.close()
    wurzel.handlers = vorher


def test_legt_verzeichnis_und_dateien_an(eigenes_log_verzeichnis) -> None:
    assert not eigenes_log_verzeichnis.exists()
    logger.setup_logging()
    logging.info("eine Zeile")

    assert eigenes_log_verzeichnis.is_dir()
    assert (eigenes_log_verzeichnis / "bot.log").exists()
    assert (eigenes_log_verzeichnis / "errors.log").exists()


def test_fehler_stehen_in_beiden_dateien(eigenes_log_verzeichnis) -> None:
    """errors.log ist die kurze Datei zum Zuerst-Hineinschauen, kein Ersatz."""
    logger.setup_logging()
    logging.info("harmlos")
    logging.error("kaputt")
    for handler in logging.getLogger().handlers:
        handler.flush()

    bot = (eigenes_log_verzeichnis / "bot.log").read_text(encoding="utf-8")
    fehler = (eigenes_log_verzeichnis / "errors.log").read_text(encoding="utf-8")
    assert "harmlos" in bot and "kaputt" in bot
    assert "kaputt" in fehler and "harmlos" not in fehler


def test_zweiter_aufruf_verdoppelt_die_handler_nicht(eigenes_log_verzeichnis) -> None:
    """
    Der Unterschied zur Vorlage: Die haengt bei jedem Aufruf neue Handler an die
    Wurzel, und jede Zeile erscheint danach doppelt.
    """
    logger.setup_logging()
    nach_dem_ersten = len(logging.getLogger().handlers)
    logger.setup_logging()
    logger.setup_logging()
    assert len(logging.getLogger().handlers) == nach_dem_ersten


def test_discord_wird_gedaempft(eigenes_log_verzeichnis) -> None:
    logger.setup_logging()
    assert logging.getLogger("discord").level == logging.WARNING
