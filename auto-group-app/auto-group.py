import os
import discord
import logging
from discord.ext import commands
from utils.secrets import access_secret_version


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Define intents
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.messages = True

# Fetch the token from the secret manager
try:
    GCP_PROJECT = os.getenv("GCP_PROJECT", False)
    if GCP_PROJECT:
        logging.info(f'GCP Project: {GCP_PROJECT}')
        token = access_secret_version(project_id=GCP_PROJECT, secret_id="discord-auto-group-app-token")
    else:
        logging.info("LOCAL")
        token = os.getenv("DISCORD_TOKEN_AGH", False)
        if not token:
            logging.error("NO TOKEN")
            raise ValueError()
except Exception as e:
    logging.error(f"Failed to fetch the token: {e}")
    raise

# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=intents)
trigger_sign = '🎧'

@bot.event
async def on_ready():
    logging.info(f'[{discord.utils.utcnow()}] Connected!')
    await bot.change_presence(status=discord.Status.online)


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel:
        if after.channel.name.startswith(trigger_sign):
            new_pos, num = await get_new_channel_properties(after.channel)
            num_str = f"0{num}" if num <= 9 else f"{num}"
            created_channel = await after.channel.clone(name=f'│ Gruppe {num_str}', reason="Auto-grouping")
            await created_channel.edit(position=new_pos, reason="Auto-grouping")
            await member.move_to(created_channel, reason="Auto-grouping")
            logging.info(f'[{discord.utils.utcnow()}] Moved user "{member.name}" ({member.id}) to voice channel "{created_channel.name}" ({created_channel.id}) at position {created_channel.position}')

    if before.channel:
        if before.channel.name.startswith('│ Gruppe') and not before.channel.members:
            await before.channel.delete(reason="Empty group channel")
            logging.info(f'[{discord.utils.utcnow()}] Deleted voice channel "{before.channel.name}" ({before.channel.id})')


async def get_grp_channels(category):
    channel_lst = []
    for channel in category.channels:
        if channel.name.startswith("│ Gruppe"):
            channel_lst.append(channel)
    return channel_lst


async def get_new_channel_properties(channel) -> (int, int):
    grp_channels = await get_grp_channels(channel.category)
    if grp_channels:
        channels_ordered = sorted(grp_channels, key=lambda obj: obj.position)
        for i in range(len(channels_ordered) - 1):
            if channels_ordered[i].position + 1 != channels_ordered[i + 1].position:
                return channels_ordered[i].position + 1, int(channels_ordered[i].name.split("Gruppe")[1]) + 1
        else:
            return channels_ordered[-1].position + 1, int(channels_ordered[-1].name.split("Gruppe")[1]) + 1
    else:
        return channel.position + 1, 1

bot.run(token)
