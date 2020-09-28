'''
https://discord.com/api/oauth2/authorize?bot_id=760125323580276757&permissions=8&scope=bot
'''

import discord
from discord import message
from discord.ext import commands
from discord.ext.commands import CommandNotFound
from discord.ext.commands import MissingRequiredArgument
import traceback
import asyncio
import datetime

import nConfig
import nHelperFunctions

bot = commands.Bot(command_prefix=nConfig.prefix)
#bot.owner_id = nConfig.ownerID

@bot.event
async def on_error(event, *args, **kwargs):
    embed = discord.Embed(title=f'new Error in event {event}()')
    embed.color = discord.Color.red()
    embed.description = f"```{traceback.format_exc()}```"
    embed.set_footer(text=kwargs)
    await bot.get_user(nConfig.ownerID).send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound) or isinstance(error, MissingRequiredArgument):
        return
    embed = discord.Embed(title=f'new Error in command {ctx.command}()')
    embed.color = discord.Color.red()
    embed.description = f"```{error}```"
    embed.set_footer(text=type(error))
    await bot.get_user(nConfig.ownerID).send(embed=embed)

@bot.event
async def on_ready():
    print(f'Welcome.\nLogged in as {bot.user}, {bot.user.id}.')
    activity = discord.Activity(type=discord.ActivityType.watching, name=nConfig.statusMessage)
    await bot.change_presence(activity=activity, status=discord.enums.Status.dnd)

@bot.listen()
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id == nConfig.memeChannelID and len(message.attachments) > 0:
        await message.add_reaction(nHelperFunctions.getEmoji(bot, nConfig.upvoteEmoji))
        await message.add_reaction(nHelperFunctions.getEmoji(bot, nConfig.downoteEmoji))

@bot.command()
async def test(ctx, *, arg):
    emoji = nHelperFunctions.getEmoji(bot, arg)
    if emoji == None:
        return
    await ctx.send(emoji)

@bot.command()
async def a(ctx):
    nHelperFunctions.updateConfig()
    await ctx.send(nConfig.prefix)


@bot.command()
@commands.is_owner()
async def emotes(ctx):
    e = discord.Embed(title="Emotes:")
    emotes = [f"<:{e.name}:{e.id}>" for e in bot.emojis]
    e.description = ''.join(emotes)
    e.timestamp = datetime.datetime.now()
    e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
    m = await ctx.send(embed=e)
    for i in range(min(20, len(emotes))):
        await m.add_reaction(emotes[i])
    

async def checkGmoWebsite():
    while True:
        await asyncio.sleep(3)
        news = await nHelperFunctions.getGmoNews()
        if news != None:
            channel = bot.get_channel(nConfig.newsChannelID)
            await channel.send(channel.guild.get_role(nConfig.gmoRoleID).mention + " " + news)

bot.loop.create_task(checkGmoWebsite())
bot.run(nConfig.token)
