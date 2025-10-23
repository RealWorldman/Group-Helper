"""
Raid Helper API Integration
"""
import logging
import aiohttp
from discord import TextChannel

from utils.secrets import get_raid_helper_api_key


async def create_event(
    channel: TextChannel,
    user_id: str,
    date: str,
    time: str,
    title: str,
    desc: str,
    template_id: int,
    gcp_project: str | bool = False,
    secrets_path: str | bool = False
) -> aiohttp.ClientResponse | None:
    """
    Erstellt ein Raid Helper Event im angegebenen Channel.

    Args:
        channel: Discord TextChannel für das Event
        user_id: Discord User ID des Event-Leaders
        date: Datum im Format YYYY-MM-DD
        time: Zeit im Format HH:MM
        title: Event-Titel
        desc: Event-Beschreibung
        template_id: Raid Helper Template ID
        gcp_project: GCP Projekt für Secrets (optional)
        secrets_path: Pfad zu lokalen Secrets (optional)

    Returns:
        ClientResponse bei Erfolg, None bei Fehler
    """
    try:
        server_id = channel.guild.id
        channel_id = channel.id

        # API Key abrufen
        raid_helper_api_key = get_raid_helper_api_key(
            project_id=gcp_project,
            secret_id=f"rhak-{server_id}",
            json_path=secrets_path
        )

        # API Request vorbereiten
        url = f'https://raid-helper.dev/api/v2/servers/{server_id}/channels/{channel_id}/event'
        headers = {
            'Authorization': raid_helper_api_key,
            'Content-Type': 'application/json;charset=utf-8'
        }
        details_event = {
            'leaderId': user_id,
            'templateId': template_id,
            'date': date,
            'time': time,
            'title': title,
            'description': desc
        }

        # API Request ausführen
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=details_event) as response:
                    response.raise_for_status()
                    logging.info(f"Raid Helper Event erstellt: {title} am {date} {time}")
                    return response
            except aiohttp.ClientError as e:
                logging.error(f"Raid Helper API Fehler: {e}")
                return None

    except Exception as e:
        logging.error(f"Fehler beim Erstellen des Raid Helper Events: {e}")
        return None

