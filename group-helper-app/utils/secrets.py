"""
Secrets Management für Group Helper Bot
Lädt Secrets aus lokaler JSON-Datei.
"""
import logging
import json
from pathlib import Path


def load_secrets_from_file(json_path: str) -> dict | None:
    """
    Lädt Secrets aus JSON-Datei.

    Args:
        json_path: Pfad zur JSON-Datei mit Secrets

    Returns:
        Dictionary mit Secrets oder None bei Fehler
    """
    try:
        file_path = Path(json_path)
        if not file_path.exists():
            logging.error(f"Secrets-Datei nicht gefunden: {json_path}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            secrets = json.load(f)
            logging.info(f"Secrets erfolgreich geladen aus: {json_path}")
            return secrets

    except FileNotFoundError:
        logging.error(f"Fehler: Datei nicht gefunden unter '{json_path}'")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Fehler: Ungültiges JSON-Format in '{json_path}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unerwarteter Fehler beim Laden der Secrets: {e}")
        return None


def get_raid_helper_api_key(secret_id: str, json_path: str) -> str | None:
    """
    Holt den Raid Helper API Key aus der Secrets-Datei.

    Args:
        secret_id: Secret ID im Format "rhak-{ServerID}"
        json_path: Pfad zur JSON-Datei mit Secrets

    Returns:
        API Key oder None bei Fehler
    """
    if not json_path:
        logging.error("Kein json_path angegeben für Raid Helper API Key")
        return None

    secrets = load_secrets_from_file(json_path)
    if not secrets:
        return None

    # Server ID aus secret_id extrahieren (z.B. "rhak-123456789" -> "123456789")
    server_id = secret_id.split("-")[-1]

    # API Key für Server suchen
    for server in secrets.get("RAID-HELPER", []):
        if str(server.get("ServerID")) == server_id:
            api_key = server.get("ApiKey")
            if api_key:
                logging.info(f"Raid Helper API Key gefunden für Server ID: {server_id}")
                return api_key

    logging.warning(f"Kein Raid Helper API Key gefunden für Server ID: {server_id}")
    return None


def get_discord_token(secret_id: str, json_path: str) -> str | None:
    """
    Holt den Discord Bot Token aus der Secrets-Datei.

    Args:
        secret_id: App-Name (z.B. "discord-group-helper-app-token")
        json_path: Pfad zur JSON-Datei mit Secrets

    Returns:
        Discord Token oder None bei Fehler
    """
    if not json_path:
        logging.error("Kein json_path angegeben für Discord Token")
        return None

    secrets = load_secrets_from_file(json_path)
    if not secrets:
        return None

    # Discord Token für App suchen
    for app in secrets.get("DISCORD", []):
        if app.get("AppName") == secret_id:
            token = app.get("DiscordToken")
            if token:
                logging.info(f"Discord Token gefunden für App: {secret_id}")
                return token

    logging.warning(f"Kein Discord Token gefunden für App: {secret_id}")
    return None
