import discord

import os
import discord
import logging
from discord.ext import commands
from discord import app_commands
from utils.secrets import access_secret_version

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

# Fetch the token from the secret manager
GCP_PROJECT = os.getenv("GCP_PROJECT")
logging.info(f'GCP Project: {GCP_PROJECT}')
# token = access_secret_version(project_id=GCP_PROJECT, secret_id="discord-token")
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
guild_id = discord.Object(id=GUILD_ID)

# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=intents)
trigger_sign = '🎧'

async def get_raid_helper_api_key():
    api_key = os.getenv("RAID_HELPER_API_KEY")
    return api_key


async def create_group_event(channel):
    server_id = channel.guild.id
    channel_id = channel.id
    api_key = await get_raid_helper_api_key()
    url = f'https://raid-helper.dev/api/v2/servers/{server_id}/channels/{channel_id}/event'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    #
    # response = requests.get(url, headers=headers)


@bot.event
async def on_ready():
    logging.info(f'[{discord.utils.utcnow()}] Connected!')

    try:
        synced = await bot.tree.sync(guild=guild_id)
        logging.info(f'Synced {len(synced)} commands to guild {guild_id.id}')
    except Exception as e:
        logging.warning(f'Error syncing commands: {e}')

    await bot.change_presence(status=discord.Status.online)

# Slash Command: /ping
@bot.tree.command(name="ping", guild=guild_id)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message('Pong!')

# Slash Command: /hello
@bot.tree.command(name="hello", guild=guild_id)
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello {interaction.user.name}, how's it going?")


# Run the bot with your token
bot.run(TOKEN)
