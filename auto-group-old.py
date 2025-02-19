import os
import discord
from keep_alive import keep_alive

client = discord.Client()

base_channel_sign = "🎧"

@client.event
async def on_voice_state_update(member, before, after):

  if after.channel is not None:
    if after.channel.name.startswith(base_channel_sign):
      new_position = get_new_channel_position(after.channel.category)
      new_channel = await after.channel.clone(name=f"{new_position} - {after.channel.category}")
      new_channel.position = new_position
      await new_channel.move(offset=new_position, beginning=True)
      await member.move_to(channel=new_channel)

  if before.channel is not None:
    if " - " in before.channel.name and len(before.channel.members) == 0:
      await before.channel.delete()


@client.event
async def on_ready():
  print("We have logged in as {0.user}".format(client))


def get_missing_no(lst):
  l = len(lst)
  total = (l + 1)*(l + 2)/2
  lst_sum = sum(lst)
  missing_num = total - lst_sum
  if missing_num == 0:
    return int(lst[-1] + 1)
  else:
    return int(missing_num)


def get_new_channel_position(category):
  position_lst = []
  for channel in category.channels:
    if channel.type == discord.ChannelType.voice and not channel.name.startswith(base_channel_sign):
      position_lst.append(channel.position)
  missing_position = get_missing_no(position_lst)
  return missing_position

keep_alive()
client.run(os.environ['TOKEN'])




