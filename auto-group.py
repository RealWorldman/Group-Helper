import os

import discord
from discord.ext import commands

# Define intents
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.messages = True

# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=intents)
token = os.getenv("DISCORD_TOKEN")  # Replace with your actual bot token

@bot.event
async def on_ready():
    print(f'[{discord.utils.utcnow()}] Connected!')

    # Set the online status.
    await bot.change_presence(status=discord.Status.online)

    # Order the channels.
    await order_channels()


@bot.event
async def on_voice_state_update(member, before, after):
    # Check if the user entered a new channel.
    if after.channel:
        # If the user entered a game channel (prefixed with a game controller unicode emoji), group them into their own channel.
        if after.channel.name.startswith('🎧'):
            created_channel = await after.channel.clone(name='│ Group', reason="Auto-grouping")
            await define_channel_pos(after.channel.category)
            await created_channel.edit(bitrate=96000, position=after.channel.position + 50,
                                       user_limit=after.channel.user_limit)
            await member.move_to(created_channel, reason="Auto-grouping")
            print(
                f'[{discord.utils.utcnow()}] Moved user "{member.name}" ({member.id}) to voice channel "{created_channel.name}" ({created_channel.id}) at position {created_channel.position}')

    # Check if the user came from another channel.
    if before.channel:
        # Delete the user's now empty temporary channel, if applicable.
        if before.channel.name.startswith('│ Group') and not before.channel.members:
            await before.channel.delete(reason="Empty group channel")
            print(f'[{discord.utils.utcnow()}] Deleted voice channel "{before.channel.name}" ({before.channel.id})')


@bot.event
async def on_guild_channel_create(channel):
    if not channel.name.startswith('│ Group'):
        await order_channels()


@bot.event
async def on_guild_channel_delete(channel):
    if not channel.name.startswith('│ Group'):
        await order_channels()


async def define_channel_pos(category):
    channel_lst = []
    for channel in category.channels:
        if channel.name.startswith("│ Group"):
            channel_lst.append(channel)
    print(channel_lst)


async def order_channels(category):
    # Get a list of channels.
    guild = next(iter(bot.guilds), None)  # Assuming the bot is in only one guild for simplicity
    if not guild:
        return

    channel_lst = []
    for channel in category.channels:
        if channel.type == discord.ChannelType.voice and channel.name.startswith("│ Group"):
            channel_lst.append(channel)


    # Sort channels by their current position.
    channels_ordered = channel_lst.sort(key=lambda x: x.position)
    channel_count = len(channels_ordered)
    channel_numbers = list(range(1, channel_count + 1))
    channel_extracted_nums = [channel.name.split("│ Group")[1] for channel in channels_ordered]




    # Re-sort channels to support auto-grouping and maximum voice quality.
    current_position = 100
    # for channel in channels_ordered:
    #
    #     current_position += 100


bot.run(token)
