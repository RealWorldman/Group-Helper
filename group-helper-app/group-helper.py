import os
import discord
from discord import TextChannel, Interaction
import logging
import asyncio
import aiohttp
from discord.ext import commands

from utils.secrets import get_raid_helper_api_key, get_discord_token
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

utc_plus_one = timezone(timedelta(hours=1))
delete_delay = 24

bot = commands.Bot(command_prefix='!', intents=intents)
trigger_sign = '🎧'
GCP_PROJECT = os.getenv("GCP_PROJECT", False)
secrets_path = os.getenv("SECRETS_PATH", False)
DEBUG = False
if DEBUG:
    guild_id = 1307336750661632121 #721276314065305662 Epilog: 1307336750661632121
    guild_obj = discord.Object(id=guild_id)
else:
    guild_id = None
    guild_obj = None

token = get_discord_token(GCP_PROJECT, "discord-group-helper-app-token", secrets_path)

async def create_group_event(channel: TextChannel, user_id: str, date: str, time: str, title: str, desc: str):
    try:
        server_id = channel.guild.id
        channel_id = channel.id
        raid_helper_api_key = get_raid_helper_api_key(project_id=GCP_PROJECT,
                                                      secret_id=f"rhak-{server_id}",
                                                      json_path=secrets_path)
        url = f'https://raid-helper.dev/api/v2/servers/{server_id}/channels/{channel_id}/event'
        headers = {
            'Authorization': raid_helper_api_key,
            'Content-Type': 'application/json;charset=utf-8'
        }
        details_event = {
            'leaderId': user_id,
            'templateId': 2,
            'date': date,
            'time': time,
            'title': title,
            'description': desc
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=details_event) as response:
                    response.raise_for_status()  # Will raise an HTTPError for bad responses
                    return response
            except aiohttp.ClientError as e:
                logging.error(f"Error during API request: {e}")
                await channel.send("There was an error while creating the event.")
    except Exception as e:
        logging.error(f"Failed to create group event: {e}")
        await channel.send("There was an error while creating the event.")

async def delete_channel(base_channel: TextChannel, new_channel: TextChannel, created_time):
    try:
        delete_time = created_time + timedelta(hours=delete_delay)
        delay = (delete_time - created_time).total_seconds()
        await base_channel.send(f"The channel {new_channel.name} will be deleted at {delete_time.strftime('%Y-%m-%d %H:%M')}.")
        await asyncio.sleep(delay)
        await new_channel.delete()
        await base_channel.send(f"The channel {new_channel.name} has been deleted.")
    except Exception as e:
        logging.error(f"Failed to delete channel: {e}")
        await base_channel.send(f"Failed to delete the channel {new_channel.name}.")

@bot.tree.command(name="group-event", guild=guild_obj) # guild=guild_id
async def group_event(interaction: Interaction, date: str, time: str, title: str, desc: str):
    try:
        channel = interaction.channel
        user_id = str(interaction.user.id)
        date_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        date_time = date_time.replace(tzinfo=utc_plus_one)

        if (datetime.now(utc_plus_one) - date_time).total_seconds() >= 0:
            await interaction.response.send_message("Gruppen Event liegt in der Vergangenheit!")
        else:
            date_time_short = datetime.strftime(date_time, '%d-%m-%Y')
            new_channel = await channel.clone(name=f"{title}-{date_time_short}", reason="Group-Event")
            response = await create_group_event(new_channel, user_id, date, time, title, desc)

            if response.status == 200:
                await interaction.response.send_message("Gruppen Event erstellt!")
            else:
                await interaction.response.send_message("Gruppen Event konnte nicht erstellt werden!")
            await delete_channel(channel, new_channel, date_time)
    except Exception as e:
        logging.error(f"Failed to execute group_event command: {e}")
        await interaction.response.send_message("There was an error while executing the command.")

@bot.event
async def on_ready():
    logging.info(f'[{discord.utils.utcnow()}] Connected!')

    await bot.change_presence(status=discord.Status.online)

    # Synchronisiere die Befehle nur für deine spezifische Guild
    guild = bot.get_guild(guild_id)
    if guild:
        await bot.tree.sync(guild=guild)
        logging.info(f"Slash commands synced for guild: {guild.name} ({guild.id})")
    else:
        logging.warning(f"Guild with ID {guild_id} not found.")

bot.run(token)
