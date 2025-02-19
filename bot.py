'''
https://discord.com/api/oauth2/authorize?client_id=760125323580276757&permissions=8&scope=bot
'''

from asyncio import futures
import discord
from discord.ext import commands
from discord.ext.commands.errors import CheckFailure, CommandNotFound, NotOwner
from discord.ext.commands.errors import MissingRequiredArgument

import traceback
import datetime

import config
from helper_functions import *

intents = discord.Intents.all()
intents.messages = True
intents.presences = True
bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)
bot.owner_ids = config.OWNER_IDS



@bot.event
async def on_error(event, *args, **kwargs):
    embed = discord.Embed(title=f'new Error in event {event}()')
    embed.color = discord.Color.red()
    embed.description = f"```{traceback.format_exc()}```"
    embed.set_footer(text=kwargs)
    channel = bot.get_channel(config.LOG_CHANNEL_ID)
    await channel.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(ctx, discord.TextChannel):
        pass
    elif hasattr(ctx.command, 'on_error'):
        return
    
    error = getattr(error, 'original', error)
    if isinstance(error, CommandNotFound) or isinstance(error, MissingRequiredArgument):
        return
    if isinstance(error, NotOwner) or isinstance(error, CheckFailure):
        await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Berechtigung diesen Command auszuführen.", color=discord.Color.red()))
        return
    embed = discord.Embed(title=repr(error))
    embed.color = discord.Color.red()
    traceback_str = str(''.join(traceback.format_exception(
        etype=type(error), value=error, tb=error.__traceback__)))
    embed.description = f"```{traceback_str}```"
    if len(embed.description) > 2000: 
        embed.description = f"```{traceback_str[-2000:]}```"

    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.listening, name=config.STATUS_MSG)
    await bot.change_presence(activity=activity, status=discord.enums.Status.dnd)
    e = discord.Embed(title="Bot started")
    e.color = discord.Color.blurple()
    e.timestamp = datetime.datetime.utcnow()
    e.set_footer(text=bot.user.name, icon_url=bot.user.avatar_url)
    channel = bot.get_channel(config.LOG_CHANNEL_ID)
    await channel.send(embed=e)

def is_bot_dev():
    async def predicate(ctx):
        if ctx.author.id in config.OWNER_IDS:
            return True
        elif 761237826758246412 in [r.id for r in bot.get_guild(config.SERVER_ID).get_member(ctx.author.id).roles] :
            return True
        return False
    return commands.check(predicate)

class HelpCommand(commands.HelpCommand):
    """Zeigt eine hilfreiche Auflistung aller Commands"""

    async def send_bot_help(self, mapping):
        await self.send_pages()

    async def send_cog_help(self, cog):
        if len(cog.get_commands()) > 0:
            await self.send_pages(cog)
        else:
            await self.context.send("Diese Kategorie beinhaltet keine Commands.")

    async def can_run_cmd(self, cmd):
        try:
            return await cmd.can_run(self.context)
        except:
            return False
        return True

    async def send_command_help(self, command):
        e = discord.Embed(title=command.name, color=discord.Color.blurple())
        cmdhelp = command.help if command.help != None else " - "
        e.description = f"```{' | '.join(command.aliases)}```" + \
            cmdhelp if len(command.aliases) > 0 else cmdhelp
        e.set_footer(icon_url=self.context.author.avatar_url)
        e.timestamp = datetime.datetime.utcnow()

        if not await self.can_run_cmd(command):
            e.color = discord.Color.red()
            e.description += "\nDu hast keine Berechtigungen, diesen Command auszuführen."
        await self.get_destination().send(embed=e)

    async def prepare_pages(self):

        pages = []
        for name in bot.cogs:
            c = bot.cogs[name]
            usable_commands = [cmd for cmd in c.get_commands() if await self.can_run_cmd(cmd)]
            if len(usable_commands) > 0:
                pages.append([name, c.description, usable_commands])
        return pages

    async def send_pages(self, page=""):
        ctx = self.context
        destination = self.get_destination()
        e = discord.Embed(color=discord.Color.blurple(), description='')
        right = "\u25B6"
        left = "\u25C0"

        pages = await self.prepare_pages()
        if page == "":
            page = 0
        # elif page.isnumeric():
        #     page = int(page) if int(page) < len(pages) else 0
        elif page in [bot.cogs[k] for k in bot.cogs.keys()]:
            page = [i for i in range(len(pages))
                    if pages[i][0] == page.qualified_name][0]

        page_count = len(pages)

        e.title = pages[page][0]
        e.description = pages[page][1]

        for cmd in pages[page][2]:
            e.add_field(name=f"{cmd.name} \n< {' | '.join(cmd.aliases)} >" if len(cmd.aliases) > 0 else cmd.name + "\n<>",
                        value=cmd.short_doc if cmd.short_doc != '' else " - ")
        e.set_footer(text=f"{page + 1} / {page_count}",
                     icon_url=ctx.author.avatar_url)

        e.timestamp = datetime.datetime.utcnow()
        msg = await destination.send(embed=e)
        await msg.add_reaction(left)
        await msg.add_reaction(right)
        active = True
        while active:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=lambda _reaction, _user: _user == ctx.author and (_reaction.emoji == right or _reaction.emoji == left) and _reaction.message == msg)
                await reaction.remove(user)
                if reaction.emoji == left and page > 0:
                    page -= 1
                elif reaction.emoji == right and page < page_count - 1:
                    page += 1
                else:
                    continue
                e.clear_fields()
                e.title = pages[page][0]
                e.description = pages[page][1]

                for cmd in pages[page][2]:
                    e.add_field(name=f"{cmd.name} \n< {' | '.join(cmd.aliases)} >" if len(cmd.aliases) > 0 else cmd.name + "\n<>",
                                value=cmd.short_doc if cmd.short_doc != '' else " - ")
                e.set_footer(text=f"{page + 1} / {page_count}",
                             icon_url=ctx.author.avatar_url)
                await msg.edit(embed=e)
            except futures.TimeoutError:
                active = False
        e.color = discord.Color.orange()
        await msg.edit(embed=e)


# Ahmads Herrschaft
class Ahmad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if after.id == 693062821650497597:
            if after.name != "Ahmad-Kult":
                await after.edit(name="Ahmad-Kult")

    @commands.Cog.listener()
    async def on_message(author, message):
        if message.channel.id == 804652343428644874 and not message.author.id in config.wortspielAllowedUserIds:
            await message.delete()


bot.load_extension("cogs.reminder")
bot.load_extension("cogs.user_messages")
bot.load_extension("cogs.wholesome")
bot.load_extension("cogs.utility")
bot.load_extension("cogs.memes")
bot.load_extension("cogs.school")
bot.load_extension("cogs.moodle")
bot.load_extension("cogs.debug")
bot.load_extension("cogs.music")
bot.load_extension("cogs.event")
bot.load_extension("cogs.news")


bot.add_cog(Ahmad(bot))


bot.help_command = HelpCommand()

bot.run(config.TOKEN)
