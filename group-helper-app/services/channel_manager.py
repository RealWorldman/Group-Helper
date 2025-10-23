"""
Channel-Verwaltung für Group Helper Bot
"""
import logging
import asyncio
import discord
from discord import TextChannel
from datetime import datetime, timedelta


async def delete_channel_after_event(
    base_channel: TextChannel,
    new_channel: TextChannel,
    event_time: datetime,
    delete_delay_hours: int,
    timezone
) -> None:
    """
    Löscht den Channel nach dem Event (nach delete_delay_hours).

    Args:
        base_channel: Original-Channel für Benachrichtigungen
        new_channel: Zu löschender Event-Channel
        event_time: Zeitpunkt des Events
        delete_delay_hours: Stunden nach Event bis zur Löschung
        timezone: Zeitzone für datetime-Berechnungen
    """
    try:
        delete_time = event_time + timedelta(hours=delete_delay_hours)
        now = datetime.now(timezone)
        delay = (delete_time - now).total_seconds()

        if delay > 0:
            await base_channel.send(
                f"Der Channel {new_channel.mention} wird am {delete_time.strftime('%d.%m.%Y um %H:%M')} Uhr "
                f"({delete_delay_hours} Stunden nach Event-Ende) gelöscht."
            )
            logging.info(f"Channel {new_channel.name} wird in {delay/3600:.1f} Stunden gelöscht")
            await asyncio.sleep(delay)

            # Prüfen ob Channel noch existiert
            if new_channel.guild.get_channel(new_channel.id):
                await new_channel.delete()
                await base_channel.send(f"✅ Der Channel **{new_channel.name}** wurde gelöscht.")
                logging.info(f"Channel {new_channel.name} erfolgreich gelöscht")
            else:
                logging.info(f"Channel {new_channel.name} wurde bereits manuell gelöscht.")
        else:
            # Event liegt in der Vergangenheit
            logging.warning(f"Event liegt bereits {abs(delay)/3600:.1f} Stunden in der Vergangenheit")
            await base_channel.send(
                f"⚠️ Event-Zeit liegt in der Vergangenheit. Channel {new_channel.mention} wird in Kürze gelöscht."
            )
            # Kurze Verzögerung, damit die Nachricht noch gelesen werden kann
            await asyncio.sleep(10)
            if new_channel.guild.get_channel(new_channel.id):
                await new_channel.delete()
                logging.info(f"Channel {new_channel.name} gelöscht (Event lag in Vergangenheit)")

    except discord.NotFound:
        logging.info(f"Channel {new_channel.name} wurde bereits gelöscht.")
    except discord.Forbidden:
        logging.error(f"Keine Berechtigung zum Löschen von Channel {new_channel.name}")
        try:
            await base_channel.send(f"❌ Keine Berechtigung zum Löschen des Channels **{new_channel.name}**.")
        except:
            pass
    except Exception as e:
        logging.error(f"Fehler beim Löschen des Channels {new_channel.name}: {e}")
        try:
            await base_channel.send(f"❌ Fehler beim Löschen des Channels **{new_channel.name}**.")
        except:
            pass


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

