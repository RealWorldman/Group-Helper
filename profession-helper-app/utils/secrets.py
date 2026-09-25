"""
Zugangsdaten aus der Secrets-Datenbank.

Angelegt wird sie mit deploy/secrets_db.sql. Bewusst eine **eigene Datenbank mit
eigener Rolle**, nicht eine Tabelle in `group-helper`: Der MCP-Server laeuft dort
mit unbeschraenktem Zugriff, und jede Agent-Sitzung koennte sonst saemtliche
Tokens im Klartext lesen.

Ein Eintrag ist ueber drei Angaben eindeutig:

    service   'discord', 'raid-helper'
    scope     App-Name oder Server-ID; '*' wenn das Geheimnis nicht pro Server anfaellt
    key_name  'token', 'api_key'

Die fruehere JSON-Datei wird nicht mehr gelesen. Ein zweites Backend haette zwei
Wahrheiten bedeutet - und die Frage "warum nimmt er den alten Token?" ist genau
die Art Fehler, die man stundenlang sucht. Wer die alten Werte uebernehmen will,
traegt sie einmal mit INSERT ein; die Zuordnung steht in deploy/secrets_db.sql.

**Werte werden nie geloggt.** Die Logs bleiben 30 Tage liegen.
"""

import logging

from sqlalchemy import Engine, create_engine, text

import config

log = logging.getLogger(__name__)

# Der Eintrag wird beim Start gelesen und gilt bis zum Neustart. Ein gewechselter
# Schluessel erreicht den Bot also erst nach einem Neustart - das ist gewollt:
# Ein Bot, der mitten im Betrieb den Token wechselt, ist schwerer zu verstehen
# als einer, den man neu startet.
_cache: dict[tuple[str, str, str], str] = {}
_engine: Engine | None = None

ABFRAGE = text(
    """
    SELECT value
      FROM credentials
     WHERE service = :service
       AND scope = :scope
       AND key_name = :key_name
       AND is_active
    """
)


def get_engine() -> Engine:
    """
    Verbindung zur Secrets-Datenbank, beim ersten Aufruf aufgebaut.

    Getrennt von services/database.py, weil es eine andere Datenbank mit einer
    anderen Rolle ist. Ein gemeinsamer Pool waere genau die Vermischung, die die
    Trennung verhindern soll.
    """
    global _engine
    if _engine is None:
        if not config.SECRETS_DATABASE_URL:
            raise RuntimeError(
                "SECRETS_DATABASE_URL ist nicht gesetzt.\n"
                "Erwartet wird z. B. "
                "postgresql+psycopg://bot_secrets_reader@host:5432/secrets\n"
                "Die Datenbank wird mit deploy/secrets_db.sql angelegt."
            )
        # Kleiner Pool: Gelesen wird beim Start, danach kaum noch.
        _engine = create_engine(config.SECRETS_DATABASE_URL, pool_size=1, pool_pre_ping=True)
    return _engine


def get_secret(service: str, key_name: str, scope: str | int = "*") -> str | None:
    """
    Holt ein Geheimnis, oder None wenn es keines gibt.

    `scope` wird zu `str` gemacht: Discord-Server-IDs sind Zahlen, in der Tabelle
    steht Text, und `123 != '123'` waere ein Fehlschlag, den man der Datenbank
    nicht ansieht.
    """
    schluessel = (service, str(scope), key_name)
    if schluessel in _cache:
        return _cache[schluessel]

    with get_engine().connect() as verbindung:
        zeile = verbindung.execute(
            ABFRAGE, {"service": service, "scope": str(scope), "key_name": key_name}
        ).first()

    if zeile is None:
        log.warning("Kein aktiver Eintrag: service=%s scope=%s key=%s", *schluessel)
        return None

    # Nur die Koordinaten des Fundes, nie der Wert.
    log.info("Geheimnis gefunden: service=%s scope=%s key=%s", *schluessel)
    _cache[schluessel] = zeile[0]
    return zeile[0]


def require_secret(service: str, key_name: str, scope: str | int = "*") -> str:
    """Wie `get_secret()`, bricht aber mit einer verwertbaren Meldung ab."""
    wert = get_secret(service, key_name, scope)
    if wert is None:
        raise RuntimeError(
            f"Kein aktiver Eintrag in der Secrets-Datenbank fuer "
            f"service='{service}', scope='{scope}', key_name='{key_name}'.\n"
            f"Anlegen mit: INSERT INTO credentials (service, scope, key_name, value) "
            f"VALUES ('{service}', '{scope}', '{key_name}', '...');"
        )
    return wert


def get_discord_token(app_name: str | None = None) -> str:
    """Der Bot-Token dieser Anwendung. Fehlt er, startet der Bot nicht."""
    return require_secret("discord", "token", app_name or config.DISCORD_APP_NAME)


def clear_cache() -> None:
    """Verwirft den Zwischenspeicher. Fuer Tests und fuer einen Schluesselwechsel."""
    _cache.clear()


def reset_engine() -> None:
    """Verwirft die Verbindung. Fuer Tests."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
