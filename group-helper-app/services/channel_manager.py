"""
Channel-Verwaltung für Group Helper Bot
"""
import logging
import asyncio
from typing import Tuple

import discord
from discord import TextChannel
from datetime import datetime, timedelta, timezone
from services.scheduler import schedule_deletion, remove_deletion


async def delete_channel_after_event(base_channel: TextChannel,
                                     new_channel: TextChannel,
                                     event_time: datetime,
                                     delete_time: datetime,
                                     restore_mode: bool = False):
    """
    Löscht den Channel nach dem Event (nach delete_delay_hours).
    """
    try:
        wait_time = (delete_time - datetime.now(timezone.utc)).total_seconds()
        if not restore_mode:
            schedule_deletion(
                channel_id=new_channel.id,
                base_channel_id=base_channel.id,
                event_time=event_time,
                delete_at=delete_time,
                event_title=new_channel.name
            )

        if wait_time > 0:
            logging.info(f"Warte {wait_time / 3600:.1f} Stunden vor Löschung von {new_channel.name}")
            await asyncio.sleep(wait_time)

        # Prüfen ob Channel noch existiert
        if new_channel.guild.get_channel(new_channel.id):
            await new_channel.delete(reason="Event-Channel nach Zeitablauf gelöscht")
            remove_deletion(new_channel.id)
            logging.info(f"Channel {new_channel.name} erfolgreich gelöscht")
        else:
            logging.warning(f"Channel {new_channel.name} wurde bereits manuell gelöscht")
            remove_deletion(new_channel.id)

    except discord.NotFound:
        logging.info(f"Channel {new_channel.name} wurde bereits gelöscht")
        remove_deletion(new_channel.id)
    except discord.Forbidden:
        logging.error(f"Keine Berechtigung zum Löschen von Channel {new_channel.name}")
    except Exception as e:
        logging.error(f"Fehler beim Löschen des Channels {new_channel.name}: {e}")


async def clone_channel_for_event(
    source_channel: TextChannel,
    title: str,
    event_date: datetime
) -> TextChannel:
    """
    Klont einen Channel für ein Event.

    Args:
        source_channel: Quell-Channel zum Klonen
        title: Event-Titel für den Channel-Namen
        event_date: Datum des Events

    Returns:
        Der geklonte TextChannel

    Raises:
        discord.Forbidden: Wenn keine Berechtigung zum Klonen
    """
    date_str = event_date.strftime('%d-%m-%Y')
    channel_name = f"{title}-{date_str}"

    new_channel = await source_channel.clone(name=channel_name, reason="Group-Event")
    logging.info(f"Channel geklont: {channel_name}")

    return new_channel

