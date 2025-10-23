"""
Logging-Konfiguration für den Group Helper Bot
"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_logging():
    """
    Konfiguriert das Logging-System mit separaten Dateien für Info und Errors.
    """
    # Logs-Verzeichnis erstellen
    os.makedirs('logs', exist_ok=True)

    # Info-Level Logs (alle Logs)
    info_handler = TimedRotatingFileHandler(
        filename='logs/bot.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)

    # Error-Level Logs (nur Errors, separate Datei für schnelleres Debugging)
    error_handler = TimedRotatingFileHandler(
        filename='logs/errors.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)

    # Console Handler für Development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter mit Dateinamen und Zeilennummer
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    info_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Logger konfigurieren
    logging.basicConfig(
        level=logging.INFO,
        handlers=[info_handler, error_handler, console_handler]
    )

    logging.info("Logging-System initialisiert")

