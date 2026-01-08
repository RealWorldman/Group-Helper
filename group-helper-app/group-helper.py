import os
import discord
from discord import Interaction, app_commands
import logging
import asyncio
from discord.ext import commands, tasks

from utils.secrets import get_discord_token
from utils.logger import setup_logging
from datetime import datetime, timedelta, timezone
from config import UTC_PLUS_ONE, DELETE_DELAY_HOURS, RAID_HELPER_TEMPLATE_ID, DEBUG, DEBUG_GUILD_ID
from validators import validate_and_parse_date, validate_and_parse_time, validate_title, validate_description
from services.raid_helper import create_event
from services.channel_manager import clone_channel_for_event, delete_channel_after_event
from services.scheduler import get_pending_deletions, remove_deletion
from services.database import init_db

# Logging initialisieren
setup_logging()

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)
secrets_path = os.getenv("SECRETS_PATH", "secrets.json")

if DEBUG:
    guild_id = DEBUG_GUILD_ID
    guild_obj = discord.Object(id=guild_id)
else:
    guild_id = None
    guild_obj = None

token = get_discord_token("discord-group-helper-app-token", secrets_path)


@bot.tree.command(name="group-event", guild=guild_obj)
@app_commands.describe(
    date="Datum (Formate: YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY)",
    time="Uhrzeit (Formate: HH:MM, HH.MM, HHMM)",
    title="Titel des Gruppen-Events",
    desc="Beschreibung des Events")
async def group_event(interaction: Interaction, date: str, time: str, title: str, desc: str):
    """
    Erstellt ein neues Gruppen-Event mit eigenem Channel und Raid Helper Integration.
    """
    try:
        # Sofort bestätigen, um Timeout zu vermeiden
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        user_id = str(interaction.user.id)

        # Validierung der Eingaben
        parsed_date, date_error = validate_and_parse_date(date)
        parsed_time, time_error = validate_and_parse_time(time)
        title_valid, title_error = validate_title(title)
        desc_valid, desc_error = validate_description(desc)

        # Validierung sammeln
        validation_errors = {
            "Datum": date_error,
            "Zeit": time_error,
            "Titel": title_error if not title_valid else None,
            "Beschreibung": desc_error if not desc_valid else None
        }

        # Nur Fehler filtern
        error_messages = [f"**{field}:** {error}" for field, error in validation_errors.items() if error]

        # Falls Fehler vorhanden (nur für User sichtbar)
        if error_messages:
            await interaction.followup.send(
                "❌ **Fehlerhafte Eingaben:**\n" + "\n".join(error_messages)
            )
            logging.warning(f"Validierungsfehler von User {interaction.user.name}: {', '.join(error_messages)}")
            return

        # DateTime-Objekt aus validierten Werten erstellen
        hour, minute = parsed_time
        event_datetime = parsed_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Prüfen ob Event in der Zukunft liegt
        if datetime.now() >= event_datetime:
            await interaction.followup.send(
                "❌ Das Gruppen-Event liegt in der Vergangenheit!"
            )
            logging.warning(f"Event-Erstellung abgelehnt: Event liegt in Vergangenheit ({event_datetime})")
            return

        # Channel klonen
        try:
            new_channel = await clone_channel_for_event(channel, title, event_datetime)
        except discord.Forbidden:
            logging.error("Bot hat keine Berechtigung, den Channel zu klonen")
            await interaction.followup.send(
                "❌ Ich habe keine Berechtigung, Channels zu erstellen!"
            )
            return

        # Raid Helper Event erstellen
        response = await create_event(
            channel=new_channel,
            user_id=user_id,
            date=date,
            time=time,
            title=title,
            desc=desc,
            template_id=RAID_HELPER_TEMPLATE_ID,
            secrets_path=secrets_path
        )

        # Erfolgsmeldung (öffentlich, damit alle den neuen Channel sehen)
        if response and response.status == 200:
            await interaction.followup.send(
                f"✅ **Gruppen-Event erstellt!**\n"
                f"📅 **Datum:** {event_datetime.strftime('%d.%m.%Y um %H:%M Uhr')}\n"
                f"📍 **Channel:** {new_channel.mention}\n"
                f"🗑️ **Löschung geplant:** {DELETE_DELAY_HOURS}h nach Event-Ende",
                ephemeral=True
            )
            logging.info(f"Event erfolgreich erstellt: {title} am {event_datetime}")

            deletion_time = event_datetime + timedelta(hours=DELETE_DELAY_HOURS)
            await delete_channel_after_event(
                base_channel=channel,
                new_channel=new_channel,
                event_time=event_datetime,
                delete_time=deletion_time
                )

        else:
            await interaction.response.send_message(
                f"⚠️ **Channel erstellt, aber Raid-Helper Event fehlgeschlagen!**\n"
                f"📍 **Channel:** {new_channel.mention}\n"
                f"Bitte erstelle das Event manuell oder überprüfe die API-Konfiguration.",
                ephemeral=True
            )
            logging.error(f"Raid Helper Event konnte nicht erstellt werden für: {title}")

    except Exception as e:
        logging.error(f"Unerwarteter Fehler bei Event-Erstellung: {e}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Es ist ein Fehler aufgetreten beim Ausführen des Befehls."
                )
            else:
                await interaction.followup.send(
                    "❌ Es ist ein Fehler aufgetreten beim Ausführen des Befehls."
                )
        except:
            logging.error("Konnte Fehlermeldung nicht senden")


@tasks.loop(hours=1)
async def check_scheduled_deletions():
    """Prüft alle 5 Minuten auf fällige Channel-Löschungen."""
    deletions = get_pending_deletions()
    now = datetime.now()
    logging.info(f'Prüfen von {len(deletions)} Pending Deletions')

    for deletion in deletions:
        if deletion.delete_time <= now:
            try:
                channel = bot.get_channel(deletion.new_channel_id)
                if channel:
                    await channel.delete(reason="Event-Channel nach Zeitablauf gelöscht")
                    logging.info(f"Channel {channel.name} erfolgreich gelöscht")
                else:
                    logging.warning(f"Channel {deletion.new_channel_id} existiert nicht mehr")

                remove_deletion(deletion.new_channel_id)
            except Exception as e:
                logging.error(f"Fehler beim Löschen von Channel {deletion.new_channel_id}: {e}")


@bot.event
async def on_ready():
    """
    Event-Handler für Bot-Start.
    """
    logging.info(f'Bot verbunden als {bot.user.name} ({bot.user.id})')
    logging.info(f'Discord.py Version: {discord.__version__}')

    init_db()
    check_scheduled_deletions.start()

    await bot.change_presence(status=discord.Status.online)

    # Synchronisiere die Befehle
    if guild_id:
        guild = bot.get_guild(guild_id)
        if guild:
            await bot.tree.sync(guild=guild)
            logging.info(f"Slash commands synchronisiert für Guild: {guild.name} ({guild.id})")
        else:
            logging.warning(f"Guild mit ID {guild_id} nicht gefunden.")
    else:
        # Global sync (falls DEBUG=False)
        await bot.tree.sync()
        logging.info("Slash commands global synchronisiert")


if __name__ == "__main__":
    logging.info("Starte Group Helper Bot...")
    bot.run(token)
