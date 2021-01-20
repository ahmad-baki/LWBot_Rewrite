'''
https://discord.com/api/oauth2/authorize?bot_id=760125323580276757&permissions=8&scope=bot
'''

from asyncio import futures
import discord
from discord.colour import Color
from discord.ext import commands
from discord.ext import tasks
from discord.errors import HTTPException
from discord.ext.commands.errors import CheckFailure, CommandNotFound, NotOwner
from discord.ext.commands.errors import MissingRequiredArgument

import traceback
import asyncio
import datetime
import operator
import validators
import ast
import json
import random
import aiohttp
import requests
from collections import defaultdict

import lwConfig as config
from lwHelperFunctions import *
import voteListHandler
import reminderHandler
import substitutionHandler

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
    error = getattr(error, 'original', error)
    if isinstance(error, CommandNotFound) or isinstance(error, MissingRequiredArgument):
        return
    if isinstance(error, NotOwner) or isinstance(error, CheckFailure):
        await ctx.send(embed=simpleEmbed(ctx.author, "Du hast keine Berechtigung diesen Command auszuführen.", color=discord.Color.red()))
        return
    embed = discord.Embed(title=repr(error))
    embed.color = discord.Color.red()
    traceback_str = str(''.join(traceback.format_exception(
        etype=type(error), value=error, tb=error.__traceback__)))
    embed.description = f"```{traceback_str}```"
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.watching, name=config.STATUS_MSG)
    await bot.change_presence(activity=activity, status=discord.enums.Status.dnd)
    e = discord.Embed(title="Bot started")
    e.color = discord.Color.blurple()
    e.timestamp = datetime.datetime.utcnow()
    e.set_footer(text=bot.user.name, icon_url=bot.user.avatar_url)
    channel = bot.get_channel(config.LOG_CHANNEL_ID)
    await channel.send(embed=e)

def is_bot_dev():
    async def predicate(ctx):
        if ctx.author.id in bot.owner_ids:
            return True
        elif 761237826758246412 in [r.id for r in bot.get_guild(config.SERVER_ID).get_member(ctx.author.id).roles] :
            return True
        return False
    return commands.check(predicate)

class Debug(commands.Cog):
    """Commands zum debuggen"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx, *, arg):
        """Test-command zum debuggen."""
        return

    @commands.command()
    async def emotes(self, ctx):
        """Zeigt alle für Norman verfügbaren Emotes an
            nutze
            `getEmoji(bot, "emojiName")`
            um einen Emoji anhand seines Namens zu erhalten (devs only)"""
        e = discord.Embed(title="Emotes:")
        emotes = [f"<:{e.name}:{e.id}>" for e in bot.emojis]
        e.description = ''.join(emotes)
        e.timestamp = datetime.datetime.utcnow()
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        m = await ctx.send(embed=e)
        # for i in range(min(20, len(emotes))):
        #    await m.add_reaction(emotes[i])


class Erinnerungen(commands.Cog):
    """Commands zum Bedienen der Erinnerungs-funktion"""

    def __init__(self, bot):
        self.bot = bot
        self.checkReminder.start()

    @commands.command(aliases=["remindme", "remind", "reminder"])
    async def setreminder(self, ctx, *, arg):
        """Erstellt eine neue Erinnerung
            nutze das Schema
            `reminder (d)d.(m)m.yyyy (h)h:(m)m`
            Beispiel: `reminder 1.10.2020 6:34`"""
        try:
            length = min(len(arg.split()), 2)
            time_str = ' '.join(arg.split()[:length])
            time = datetime.datetime.strptime(time_str, '%d.%m.%Y %H:%M')
            if time < datetime.datetime.now():
                await ctx.send(embed=simpleEmbed(ctx.author, "Erinnerungen in der Vergangenheit sind nicht erlaubt.", color=discord.Color.orange()))
                return
            await ctx.send(embed=simpleEmbed(ctx.author, "Bitte gib deine Erinnerungsnachricht ein.", "Dies ist nur in den nächsten 60s möglich.", color=discord.Color.gold()))
            m = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
        except ValueError:
            await ctx.send(embed=simpleEmbed(ctx.author, "Dein Datum ist so nicht zulässig.", "Das Format sollte so aussehen:\n```reminder (d)d.(m)m.yyyy (h)h:(m)m\nBeispiel: reminder 1.10.2020 6:34```", color=discord.Color.red()))
            return
        except futures.TimeoutError:
            await ctx.send(embed=simpleEmbed(ctx.author, "Die Zeit ist abgelaufen.", "Bitte versuche es erneut, falls du eine Erinnerung erstellen möchtest.", color=discord.Color.red()))
            return
        except Exception:
            await ctx.send(embed=simpleEmbed(ctx.author, "Ein Fehler ist aufgetreten", "Deine Erinnerung konnte nicht gespeichert werden.", color=discord.Color.red()))
        else:
            if len(ctx.message.mentions) > 0:
                for recipient in ctx.message.mentions:
                    reminderHandler.addReminder(
                        ctx.author.id, recipient.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                    await ctx.send(embed=simpleEmbed(ctx.author, "Eine neue Erinnerung für " + recipient.name + ", " + time_str + " wurde erstellt.", m.content))
            if len(ctx.message.role_mentions) > 0:
                for role in ctx.message.role_mentions:
                    reminderHandler.addReminder(
                        ctx.author.id, role.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                    await ctx.send(embed=simpleEmbed(ctx.author, "Eine neue Erinnerung für @" + role.name + ", " + time_str + " wurde erstellt.", m.content))
            if len(ctx.message.mentions) == len(ctx.message.role_mentions) == 0:
                reminderHandler.addReminder(
                    ctx.author.id, ctx.author.id, time_str, m.content + f"\n_[Hier]({ctx.message.jump_url}) erstellt_")
                await ctx.send(embed=simpleEmbed(ctx.author, "Eine neue Erinnerung für dich, " + time_str + " wurde erstellt.", m.content))
            return

    @commands.command(aliases=["mr"])
    async def myreminders(self, ctx):
        """Listet alle Erinnerungen eines Nutzers auf"""
        reminder = reminderHandler.getReminder()
        if str(ctx.author.id) in list(reminder.keys()) and len(reminder[str(ctx.author.id)]) > 0:
            e = discord.Embed(title="Deine Erinnerungen", color=ctx.author.color,
                              timestamp=datetime.datetime.utcnow())
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
            for singleReminder in reminder[str(ctx.author.id)]:
                e.add_field(name=singleReminder[0],
                            value=singleReminder[1], inline=False)
            await ctx.send(embed=e)
        else:
            await ctx.send(embed=simpleEmbed(ctx.author, "Du hast keine Erinnerungen.",
                                                               f"Gebe {bot.command_prefix}reminder [Datum], um eine neue Erinnerung zu erstellen oder " +
                                                               f"{bot.command_prefix}help reminder ein, um dir die korrekte Syntax des Commandes anzeigen zu lassen."))

    @commands.command(aliases=["rmr"])
    async def removereminder(self, ctx):
        """Erinnerung entfernen
            rufe `,removereminder` auf, und wähle dann den Index der zu entfernenden Erinnerung"""
        reminder = reminderHandler.getReminder()
        if str(ctx.author.id) in list(reminder.keys()) and len(reminder[str(ctx.author.id)]) > 0:
            e = discord.Embed(title="Deine Erinnerungen", color=ctx.author.color,
                              timestamp=datetime.datetime.utcnow())
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
            reminderCount = len(reminder[str(ctx.author.id)])
            for i in range(reminderCount):
                singleReminder = reminder[str(ctx.author.id)][i]
                e.add_field(name=f"[{i}] {singleReminder[0]}",
                            value=singleReminder[1], inline=False)

            await ctx.send(embed=e)
            await ctx.send(embed=simpleEmbed(ctx.author, "Gebe bitte den Index der Erinnerung ein, die du löschen möchtest.",
                                                               "Dies ist nur in den nächsten 60s möglich.", color=discord.Color.gold()))
            try:
                m = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
                index = int(m.content)
                if 0 <= index < reminderCount:
                    reminderHandler.removeReminder(
                        ctx.author.id, *reminder[str(ctx.author.id)][index])
                    await ctx.send(embed=simpleEmbed(ctx.author, "Die Erinnerung wurde erfolgreich gelöscht.",
                                                                       f"Deine Erinnerung\n```{''.join(reminder[str(ctx.author.id)][index][1].splitlines()[:-1])}``` wurde gelöscht."))
                else:
                    raise ValueError
            except futures.TimeoutError:
                await ctx.send(embed=simpleEmbed(ctx.author, "Die Zeit ist abgelaufen.",
                                                                   "Bitte versuche es erneut, falls du eine Erinnerung löschen möchtest.", color=discord.Color.red()))
            except ValueError:
                await ctx.send(embed=simpleEmbed(ctx.author, "Eingabefehler",
                                                                   "Deine Eingabe war keine der zulässigen aufgeführten Indices.", color=discord.Color.red()))
        else:
            await ctx.send(embed=simpleEmbed(ctx.author, "Du hast keine Erinnerungen.",
                                                               f"Gebe {bot.command_prefix}reminder [Datum], um eine neue Erinnerung zu erstellen oder " +
                                                               f"{bot.command_prefix}help reminder ein, um dir die korrekte Syntax des Commandes anzeigen zu lassen."))

    @tasks.loop(seconds=30)
    async def checkReminder(self):
        r = reminderHandler.getReminder()
        now = datetime.datetime.now()
        recipients = list(r.keys())
        for recipientID in recipients:
            for reminder in r[recipientID]:
                time = datetime.datetime.strptime(
                    reminder[0], '%d.%m.%Y %H:%M')
                if time <= now:
                    channel = bot.get_channel(config.BOT_CHANNEL_ID)
                    author = bot.get_guild(
                        config.SERVER_ID).get_member(int(reminder[2]))
                    recipient = bot.get_guild(
                        config.SERVER_ID).get_member(int(recipientID))
                    if recipient == None:
                        recipient = bot.get_guild(
                            config.SERVER_ID).get_role(int(recipientID))
                    if recipient == None:
                        return
                    color = recipient.color
                    await channel.send(content=recipient.mention, embed=simpleEmbed(author, "Erinnerung", reminder[1], color=color))
                    reminderHandler.removeReminder(recipientID, *reminder)

    @checkReminder.before_loop
    async def beforeReminderCheck(self):
        await bot.wait_until_ready()
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "reminder loop start", color=discord.Color.green()))

    @checkReminder.after_loop
    async def afterReminderCheck(self):
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "reminder loop stopped.", color=discord.Color.orange()))
        await asyncio.sleep(60)
        self.checkReminder.restart()

    @checkReminder.error
    async def ReminderCheckError(self, error):
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "reminder error", color=discord.Color.orange()))
        await on_command_error(bot.get_channel(config.LOG_CHANNEL_ID), error)


class Stundenplan(commands.Cog):
    """Commands zum Nutzen des personalisierten Stundenplans"""

    def __init__(self, bot):
        self.bot = bot
        self.updateSubstitutionPlan.start()

    @commands.command()
    async def kurse(self, ctx):
        """Listet alle Kurse eines Nutzers auf"""
        # give the ctx.author the course seperator role if he does not have it already
        if not config.ROLE_SEPERATOR_ID in [c.id for c in ctx.author.roles]:
            await ctx.author.add_roles(ctx.guild.get_role(config.ROLE_SEPERATOR_ID))
        # if the ctx.author has at least one course role, send it
        kurse = substitutionHandler.getMyCourseRoleNames(ctx.author)
        if len(kurse) > 0:
            await ctx.send(embed=simpleEmbed(ctx.author, "Deine Kurse: ", f"```{', '.join(kurse)}```"))
        # otherwise, inform the ctx.author that he does not have any course roles
        else:
            await ctx.send(embed=simpleEmbed(ctx.author, "Du hast keine Kurse ausgewählt. ",
                                                               "Verwende den command addKurse [kurs1 kurs2 ...] um mehr hinzuzufügen.\nBeispiel: ```addKurse EN4 PH1```\ngibt dir die Kursrollen EN4 und PH1."))

    @commands.command(aliases=["ak"])
    async def addKurse(self, ctx, *, args):
        """Gibt dem Nutzer die gewünschten Kurse
            beispiel: `,addkurse MA1 IN2 de2 mu1"""
        args = args.split(" ")
        # give the ctx.author the course seperator role if he does not have it already
        if not config.ROLE_SEPERATOR_ID in [c.id for c in ctx.author.roles]:
            await ctx.author.add_roles(ctx.guild.get_role(config.ROLE_SEPERATOR_ID))
        # for all roles listed to add
        for arg in args:
            # if the role does not exist, create it
            if arg not in substitutionHandler.getMyCourseRoleNames(ctx.guild):
                await substitutionHandler.createCourseRole(ctx, arg)
            # if the ctx.author does not already have the role, add it
            if arg not in substitutionHandler.getMyCourseRoleNames(ctx.author):
                roleID = [r.id for r in substitutionHandler.getMyCourseRoles(
                    ctx.guild) if r.name == arg][0]
                await ctx.author.add_roles(ctx.guild.get_role(roleID))

        kurse = substitutionHandler.getMyCourseRoleNames(ctx.author)
        await ctx.send(embed=simpleEmbed(ctx.author, "Deine Kurse: ", f"```{', '.join(kurse)}```"))

    @commands.command(aliases=["rk"])
    async def removeKurse(self, ctx, *, args):
        """Entfernt die gewünschten Kurse des Nutzers
            beispiel: `,removeKurse MA1 IN2 de2 mu1"""
        args = args.split(" ")
        # give the ctx.author the course seperator role if he does not have it already
        if not config.ROLE_SEPERATOR_ID in [c.id for c in ctx.author.roles]:
            await ctx.author.add_roles(ctx.guild.get_role(config.ROLE_SEPERATOR_ID))
        for arg in args:
            # check if the ctx.author has the role that he wants to remove
            if arg not in substitutionHandler.getMyCourseRoleNames(ctx.author):
                await ctx.send(embed=simpleEmbed(ctx.author, "Du besitzt diese Kursrolle nicht.", color=discord.Color.red()))
                return
            # get the role id by name
            roleID = [r.id for r in substitutionHandler.getMyCourseRoles(
                ctx.guild) if r.name == arg][0]
            # get the role by the id
            role = ctx.guild.get_role(roleID)
            await ctx.author.remove_roles(role)
            # delete the role if no members have it now
            if len(role.members) == 0:
                await role.delete(reason="Diese Kursrolle wird nicht mehr benutzt ist daher irrelevant.")
        await ctx.send(embed=simpleEmbed(ctx.author, f"Die Rolle(n) {', '.join(args)} wurde erfolgreich entfernt."))

    @commands.command(aliases=["mp"])
    async def myplan(self, ctx):
        """Zeigt den personalisierten Vertretungsplan des Nutzers an"""
        # give the ctx.author the course seperator role if he does not have it already
        if not config.ROLE_SEPERATOR_ID in [c.id for c in ctx.author.roles]:
            await ctx.author.add_roles(ctx.guild.get_role(config.ROLE_SEPERATOR_ID))
        # if the ctx.author has at least no course role, tell him and return
        kurse = substitutionHandler.getMyCourseRoleNames(ctx.author)
        if len(kurse) == 0:
            await ctx.send(embed=simpleEmbed(ctx.author, "Du hast keine Kurse ausgewählt. ",
                                                               "Verwende den command addKurse [kurs1 kurs2 ...] um mehr hinzuzufügen.\nBeispiel: ```addKurse EN4 PH1```\ngibt dir die Kursrollen EN4 und PH1."))
            return
        plan = substitutionHandler.getSubstitutionPlan()
        embed = discord.Embed(
            title="Dein persönlicher Vertretungsplan: ", color=ctx.author.color)
        embed.description = "`Stunde Art Kurs Lehrer Raum Bemerkungen`"
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        courses = substitutionHandler.getMyCourseRoleNames(ctx.author)

        e = substitutionHandler.format_plan(plan, ctx.guild, embed, courses)
        await ctx.send(embed=e)

    @tasks.loop(seconds=300)
    async def updateSubstitutionPlan(self):
        currentPlan, newPlan = await substitutionHandler.getCurrentSubstitutionPlan()
        try:
            additions = {}
            removals = {}
            for date in newPlan.keys():
                additions[date] = []
                removals[date] = []
                if date not in currentPlan.keys():
                    additions[date] = newPlan[date]
                else:
                    for k in newPlan[date]:
                        if k not in currentPlan[date]:
                            additions[date].append(k)
                    for k in currentPlan[date]:
                        if k not in newPlan[date]:
                            removals[date].append(k)
            channel = bot.get_channel(config.PLAN_CHANNEL)

            rmEmbed = discord.Embed(
                title="Entfernt", color=discord.Color.red())
            addedEmbed = discord.Embed(
                title="Neu hinzugefügt", color=discord.Color.green())
            rmEmbed.description = "gelöschte Vertretungen"
            addedEmbed.description = "geänderte Vertretungen"
            server = channel.guild
            rmEmbed.timestamp = datetime.datetime.utcnow()
            addedEmbed.timestamp = datetime.datetime.utcnow()
            rmEmbed = substitutionHandler.format_plan(
                removals, server, rmEmbed)
            addedEmbed = substitutionHandler.format_plan(
                additions, server, addedEmbed)

            if len(rmEmbed.fields) > 0:
                await channel.send(embed=rmEmbed)
            if len(addedEmbed.fields) > 0:
                await channel.send(embed=addedEmbed)
        except Exception as e:
            try:
                await on_command_error(bot.get_channel(config.LOG_CHANNEL_ID), e)
            except Exception:
                pass

    @updateSubstitutionPlan.before_loop
    async def beforeSubstitutionPlan(self):
        await bot.wait_until_ready()
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "Vertretungplan loop start", color=discord.Color.green()))

    @updateSubstitutionPlan.after_loop
    async def afterSubstitutionPlan(self):
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "Vertretungplan loop stopped.", color=discord.Color.orange()))
        await asyncio.sleep(60)
        self.updateSubstitutionPlan.restart()

    @updateSubstitutionPlan.error
    async def substitutionPlanError(self, error):
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "substitution plan error", color=discord.Color.orange()))
        await on_command_error(bot.get_channel(config.LOG_CHANNEL_ID), error)


class Memes(commands.Cog):
    """Commands zum Votingsystem im Shitpostkanal"""

    def __init__(self, bot):
        self.bot = bot

    # @commands.command()
    # async def entries(self, ctx):
    #     """Zeigt alle Memes, deren Scores für die Bestenliste gespeichert werden"""
    #     voteListHandler.deleteOldMessages()
    #     voteList = voteListHandler.getVoteList()
    #     e = discord.Embed()
    #     e.color = discord.Color.purple()
    #     e.timestamp = datetime.datetime.utcnow()
    #     e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
    #     e.set_author(name=bot.user, icon_url=bot.user.avatar_url)
    #     if not len(voteList) > 0:
    #         e.title = "Gerade eben sind keine Memes vorhanden."
    #         await ctx.send(embed=e)
    #         return
    #     e.title = "Entries"
    #     e.description = "All current entry messages in the votelist.\n\n```[ MessageID:\n Upvotes \u2606, created_at ]```"
    #     for k in list(voteList.keys()):
    #         e.add_field(
    #             name=f"{str(k)}:", value=f"```{str(voteList[k][0])} \u2606, {str(voteList[k][1])}```", inline=False)

    #     await ctx.send(embed=e)

    @commands.command()
    async def top(self, ctx):
        """Zeigt den Top-shitpost"""
        async with ctx.message.channel.typing():
            voteListHandler.deleteOldMessages()
        voteList = voteListHandler.getVoteList()
        if(len(voteList) > 0):
            vList = {}
            for i in voteList.keys():
                vList[i] = voteList[i][0]
            sortedDict = sorted(
                vList.items(), key=operator.itemgetter(1), reverse=True)
            winnerMessage = await bot.get_channel(config.MEME_CHANNEL_ID).fetch_message(sortedDict[0][0])
            score = voteList[sortedDict[0][0]][0]
            e = discord.Embed()
            e.title = f"Der aktuell beliebteste Beitrag mit {str(score)} {getEmoji(bot, config.UPVOTE)}"

            e.description = f"[Nachricht:]({winnerMessage.jump_url})"
            if(len(winnerMessage.attachments) > 0):
                e.set_image(url=winnerMessage.attachments[0].url)
            e.set_author(name=winnerMessage.author,
                         icon_url=winnerMessage.author.avatar_url)
            e.color = winnerMessage.guild.get_member(
                winnerMessage.author.id).colour
            date = winnerMessage.created_at
            e.description += "\n" + winnerMessage.content
            e.timestamp = datetime.datetime.utcnow()
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.message.channel.send(embed=e)
            if(len(winnerMessage.attachments) > 0):
                if(not is_url_image(e.image.url)):
                    await ctx.message.channel.send(winnerMessage.attachments[0].url)
        else:
            await ctx.message.channel.send("Zurzeit sind keine Memes vorhanden.")

    @commands.command()
    async def stats(self, ctx, *args):
        """Wertet die Bewertungen der Shitposts der einzelnen Nutzer aus
            Dies wird aufgrund von discord rate limits lange dauern.
            Für jeden Nutzer werden Anzahl Memes, Anzahl upvotes/downvotes, upvote/downvote-Verhältnis sowie durchschnittliche upvotes/downvotes aufgelistet.
            \nAls optionale Parameter können zuerst Limit des Durchsuchens, dann auszuwertende Nutzer angegeben werden.
            \n`stats 200 @Florik3ks @Zuruniik` gibt die Daten für @Florik3ks und @Zuruniik während der letzten 200 Nachrichten (nicht Beiträge!) aus.
            \nOhne angegebene Personen werden die Daten von allen Personen, die Beiträge gepostet haben, aufgeführt.
            \nOhne ein angegebenes Nachrichtenlimit werden alle Beiträge ausgewertet."""
        if len(args) > 0:
            if not args[0].isnumeric() and len(ctx.message.mentions) == 0:
                return
        progressEmbed = discord.Embed(title="Nachrichten werden gelesen...")
        progressEmbed.description = "Dies könnte (wird) eine recht lange Zeit in Anspruch nehmen."
        progressEmbed.set_image(
            url=getEmoji(bot, "KannaSip").url)
        await ctx.send(embed=progressEmbed)
        progress = 0
        progressMsg = await ctx.send("`  0% fertig.`")
        async with ctx.channel.typing():
            channel = bot.get_channel(config.MEME_CHANNEL_ID)
            upvote = getEmoji(bot, config.UPVOTE)
            downvote = getEmoji(bot, config.DOWNVOTE)
            members = defaultdict(lambda: defaultdict(int))
            limit = None
            if len(args) > 0 and args[0].isnumeric():
                limit = int(args[0])
            messageCount = limit if limit != None else len(await channel.history(limit=None).flatten())
            counter = 0
            async for m in channel.history(limit=limit):
                counter += 1

                oldProg = progress
                progress = round(counter / messageCount * 100)
                if progress != oldProg:
                    await progressMsg.edit(content=f"`{str(progress).rjust(3)}% fertig.`")

                if len(m.reactions) > 0:
                    meme = False
                    for r in m.reactions:
                        voters = await r.users().flatten()
                        count = r.count - 1 if bot.user in voters else r.count
                        if r.emoji == upvote:
                            members[m.author.id]["up"] += count
                            meme = True
                        elif r.emoji == downvote:
                            members[m.author.id]["down"] += count
                            meme = True
                    if meme:
                        members[m.author.id]["memes"] += 1

            e = discord.Embed(title="Stats", color=ctx.author.color,
                              timestamp=datetime.datetime.utcnow())
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)

            for member_id in members.keys():
                if len(ctx.message.mentions) > 0:
                    if member_id not in [u.id for u in ctx.message.mentions]:
                        continue
                if members[member_id] == {}:
                    continue
                if members[member_id]["memes"] == 0:
                    continue
                member = bot.get_guild(config.SERVER_ID).get_member(member_id)
                up = members[member_id]['up']
                down = members[member_id]['down']
                total = members[member_id]['memes']
                ratio = round(
                    up / down, 2) if down > 0 else up if up > 0 else 1
                dvratio = "1"  # if down > 0 else "0"
                members[member_id]["ratio"] = ratio
                e.add_field(name=member.display_name, value=f"Anzahl der Beiträge: `{members[member_id]['memes']}`\n" +
                            f"`Gesamtanzahl` {str(upvote)} `{str(up).rjust(6)} : {str(down).ljust(6)}` {str(downvote)}\n" +
                            f"`Verhältnis  ` {str(upvote)} `{str(ratio).rjust(6)} : {dvratio.ljust(6)}` {str(downvote)}\n" +
                            f"`Durchschnitt` {str(upvote)} `{str(round(up / total, 2)).rjust(6)} : {str(round(down / total, 2)).ljust(6)}` {str(downvote)}",
                            inline=False
                            )

            for m in ctx.message.mentions:
                if m.id not in members.keys():
                    e.add_field(name=m.display_name, value="Anzahl der Beiträge: `0`\n" +
                                f"`Gesamtanzahl` {str(upvote)} `     0 : 0     ` {str(downvote)}\n" +
                                f"`Verhältnis  ` {str(upvote)} `     1 : 1     ` {str(downvote)}\n" +
                                f"`Durchschnitt` {str(upvote)} `     0 : 0     ` {str(downvote)}", inline=False
                                )
        await ctx.send(embed=e)

        ## Leaderboard ##
        l = discord.Embed(title="Leaderboard (Up-/Downvote Verhältnis)",
                          color=discord.Color.gold(), timestamp=datetime.datetime.utcnow())

        ratioLeaderboard = []

        for k in members.keys():
            ratioLeaderboard.append([members[k]["ratio"], k])

        ratioLeaderboard.sort(reverse=True)

        for r in ratioLeaderboard:
            member = bot.get_guild(config.SERVER_ID).get_member(r[1])
            l.add_field(name=member.display_name, value=str(r[0]))

        await ctx.send(embed=l)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == bot.user:
            return
        if message.channel.id == config.MEME_CHANNEL_ID and (len(message.attachments) > 0 or validators.url(message.content)):
            await self.addVotes(message)

    async def addVotes(self, message):
        up = getEmoji(bot, config.UPVOTE)
        down = getEmoji(bot, config.DOWNVOTE)
        await message.add_reaction(up)
        await message.add_reaction(down)
        cross = "\N{CROSS MARK}"
        await message.add_reaction(cross)
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == message.author and _reaction.emoji == cross and _reaction.message == message)
            await message.clear_reaction(up)
            await message.clear_reaction(down)
        except asyncio.TimeoutError:
            pass
        try:
            await message.clear_reaction(cross)
        except discord.errors.NotFound:
            pass
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # check if the channel of the reaction is the specified channel
        if payload.channel_id != config.MEME_CHANNEL_ID:
            return
        # get user, message and reaction
        user = bot.get_user(payload.user_id)
        msg = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = None
        for reac in msg.reactions:
            if reac.emoji == payload.emoji.name or reac.emoji == payload.emoji:
                reaction = reac
        if reaction == None:
            return

        # get up-/downvote emojis
        upvote = getEmoji(bot, config.UPVOTE)
        downvote = getEmoji(bot, config.DOWNVOTE)
        if user != bot.user:
            # in case the message author tries to up-/downvote their own post
            if reaction.message.author == user and (reaction.emoji == upvote or reaction.emoji == downvote):
                await reaction.remove(user)
                errormsg = await reaction.message.channel.send(f"{user.mention} Du darfst für deinen eigenen Beitrag nicht abstimmen.")
                deleteEmoji = getEmoji(
                    bot, config.UNDERSTOOD_EMOJI)
                await errormsg.add_reaction(deleteEmoji)
                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == user and _reaction.emoji == deleteEmoji)
                except futures.TimeoutError:
                    pass
                await errormsg.delete()
                return

            # change voting counter
            if reaction.emoji == upvote:
                voteListHandler.changeVotingCounter(reaction.message, 1)
                # pin message when it has the specified amount of upvotes
                if reaction.count - 1 >= config.REQUIRED_UPVOTES_FOR_GOOD_MEME:
                    # await reaction.message.pin(reason="good meme")
                    await self.send_good_meme(reaction.message)
            elif reaction.emoji == downvote:
                voteListHandler.changeVotingCounter(reaction.message, -1)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        # check if the channel of the reaction is the specified channel
        if payload.channel_id != config.MEME_CHANNEL_ID:
            return
        # get user, message and reaction
        user = bot.get_user(payload.user_id)
        msg = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = None
        for reac in msg.reactions:
            if reac.emoji == payload.emoji.name or reac.emoji == payload.emoji:
                reaction = reac
        if reaction == None:
            return
        # change voting counter
        if user != bot.user and user != reaction.message.author:
            if reaction.emoji == getEmoji(bot, config.UPVOTE):
                voteListHandler.changeVotingCounter(reaction.message, -1)
            elif reaction.emoji == getEmoji(bot, config.DOWNVOTE):
                voteListHandler.changeVotingCounter(reaction.message, 1)

    async def send_good_meme(self, msg, force=False):
        if not force:
            with open(config.path + '/json/goodMemes.json', 'r') as myfile:
                memes = json.loads(myfile.read())

            if msg.id in memes:
                return

            memes.append(msg.id)
            with open(config.path + '/json/goodMemes.json', 'w') as myfile:
                json.dump(memes, myfile)

        channel = bot.get_channel(config.GOOD_MEMES_CHANNEL_ID)
        e = discord.Embed()
        e.description = f"[Nachricht:]({msg.jump_url})"
        e.set_author(name=msg.author,
                     icon_url=msg.author.avatar_url)
        e.color = msg.guild.get_member(
            msg.author.id).colour
        e.description += "\n" + msg.content
        e.timestamp = msg.created_at
        e.set_footer(text=msg.author.name, icon_url=msg.author.avatar_url)

        if(len(msg.attachments) > 0):
            if(is_url_image(msg.attachments[0].url)):
                e.set_image(url=msg.attachments[0].url)
                counter = 0
                while e.image.width == 0 or counter == 100:
                    counter += 1
                    e.set_image(url=msg.attachments[0].url)
                if counter == 100:
                    await on_command_error(bot.get_channel(config.LOG_CHANNEL_ID), Exception(f"{str(msg.id)}: good meme was not sent correctly."))
                elif counter > 0:
                    await on_command_error(bot.get_channel(config.LOG_CHANNEL_ID), Exception(f"{str(msg.id)}: good meme was not sent correctly, took {counter} attempts."))

                await channel.send(embed=e)

            else:
                await channel.send(embed=e, file=await msg.attachments[0].to_file())


class Utility(commands.Cog):
    """Andere nützliche Commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def embed(self, ctx, *args):
        """Ruft die Funktion simpleEmbed(*args) mit den übergebenen Argumenten auf.
            Diese sind: `title, description = "", image_url=""`
            Zumindest der Titel muss übergeben werden, die anderen beiden sind optional.
            Wenn ein Argument aus mehreren Worten bestehen soll, müssen diese in "Wort1 Wort2" stehen."""

        await ctx.send(embed=simpleEmbed(ctx.author, *args))
        await ctx.message.delete()

    # https://gist.github.com/nitros12/2c3c265813121492655bc95aa54da6b9 geklaut und überarbeitet
    @commands.is_owner()
    @commands.command(name="eval", aliases=["ev", "evaluate"])
    async def _eval(self, ctx, *, cmd):
        """Führt Code aus und sendet das Ergebnis der letzten Zeile, falls vorhanden. (devs only)
            Beispiel: 
            ```,ev 
                for i in range(4):
                    await ctx.send(ctx.author.mention)
                "uwu"```"""
        def insert_returns(body):
            # insert return stmt if the last expression is a expression statement
            if isinstance(body[-1], ast.Expr):
                body[-1] = ast.Return(body[-1].value)
                ast.fix_missing_locations(body[-1])

            # for if statements, we insert returns into the body and the orelse
            if isinstance(body[-1], ast.If):
                insert_returns(body[-1].body)
                insert_returns(body[-1].orelse)

            # for with blocks, again we insert returns into the body
            if isinstance(body[-1], ast.With):
                insert_returns(body[-1].body)
        fn_name = "_eval_expr"

        cmd = cmd.strip("` ")

        # removes discord syntax highlighting if it exists
        if cmd.split("\n")[0] == "py":
            cmd = "\n".join(cmd.split("\n")[1:])

        # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

        # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        insert_returns(body)

        env = dict(globals(), **locals())
        # env = {
        #     'bot': ctx.bot,
        #     'discord': discord,
        #     'commands': commands,
        #     'ctx': ctx,
        #     '__import__': __import__
        # }
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = (await eval(f"{fn_name}()", env))

        try:
            if type(result) != discord.message.Message:
                await ctx.send(result)
        except HTTPException:
            pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        afkChannel = member.guild.afk_channel
        if after.channel and before.channel:  # if the member didn't just join or quit, but moved channels
            if after.channel == afkChannel and before.channel.id in config.AWAKE_CHANNEL_IDS:  # the "Stay awake" feature
                await member.move_to(before.channel)

        # the "banish" feature
        if after.channel and member.guild.get_role(config.BANISHED_ROLE_ID) in member.roles and after.channel.id != config.BANISHED_VC_ID and member.id not in bot.owner_ids:
            await member.move_to(member.guild.get_channel(config.BANISHED_VC_ID))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # move to hell if banished role was added
        hell = before.guild.get_channel(config.BANISHED_VC_ID)
        r = before.guild.get_role(config.BANISHED_ROLE_ID)
        if r in after.roles and r not in before.roles and before.id not in bot.owner_ids:
            if after.voice != None:
                if after.voice.channel != hell:
                    await after.move_to(hell)


class Schulneuigkeiten(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.checkGmoWebsite.start()

    @tasks.loop(seconds=300)
    async def checkGmoWebsite(self):
        news = await getGmoNews()
        if news != None:
            channel = bot.get_channel(config.NEWS_CHANNEL_ID)
            await channel.send(channel.guild.get_role(config.GMO_ROLE_ID).mention + " " + news)

    @checkGmoWebsite.before_loop
    async def beforeGmoNews(self):
        await bot.wait_until_ready()
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "gmoNewsCheck loop start", color=discord.Color.green()))

    @checkGmoWebsite.after_loop
    async def afterGmoNews(self):
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "gmoNewsCheck loop stopped.", color=discord.Color.orange()))
        await asyncio.sleep(60)
        self.checkGmoWebsite.restart()

    @checkGmoWebsite.error
    async def gmoNewsError(self, error):
        channel = bot.get_channel(config.LOG_CHANNEL_ID)
        await channel.send(embed=simpleEmbed(bot.user, "gmo news error", color=discord.Color.orange()))
        await on_command_error(bot.get_channel(config.LOG_CHANNEL_ID), error)


class Wholesome(commands.Cog):
    """Wholesome commands um deine Seele zu reinigen"""
    def __init__(self, bot):
        self.bot = bot
        self.cmds = ["hug", "pat", "feed", "cuddle", "kiss", "poke", "slap", "bite"]

    @commands.command()
    async def hug(self, ctx, *args):
        """umarme einen anderen Benutzer mit `hug @user`"""
        await self.send(ctx, args, "hug", "umarmt", cat_ascii="(^・ω・^ )")

    @commands.command()
    async def pat(self, ctx, *args):
        """patte einen anderen Benutzer mit `pat @user`"""
        await self.send(ctx, args, "pat", "gepattet", cat_ascii="(ฅ`･ω･´)っ=")

    @commands.command()
    async def feed(self, ctx, *args):
        """füttere einen anderen Benutzer mit `feed @user`"""
        await self.send(ctx, args, "feed", "gefüttert", cat_ascii="~(=^‥^)_旦~")

    @commands.command()
    async def cuddle(self, ctx, *args):
        """knuddle einen anderen Benutzer mit `cuddle @user`"""
        await self.send(ctx, args, "cuddle", "geknuddelt", cat_ascii="(=^･ω･^)y＝")

    @commands.command()
    async def kiss(self, ctx, *args):
        """küsse einen anderen Benutzer mit `kiss @user`"""
        await self.send(ctx, args, "kiss", "geküsst", cat_ascii="╭(╯ε╰)╮")


    @commands.command()
    async def poke(self, ctx, *args):
        """stupst einen anderen Benutzer mit `hug @user` an"""
        await self.send(ctx, args, "poke", "angestupst", cat_ascii="ヾ(=｀ω´=)ノ”")

    @commands.command()
    async def slap(self, ctx, *args):
        """schlage einen anderen Benutzer mit `slap @user`"""
        await self.send(ctx, args, "slap", "geschlagen", cat_ascii="(ↀДↀ)⁼³₌₃")

    @commands.command()
    async def bite(self, ctx, *args):
        """beiße einen anderen Benutzer mit `bite @user`"""
        await self.send(ctx, args, "bite", "gebissen", cat_ascii="(・∀・)")


    async def send(self, ctx, args, command, verb, content_type="gif", cat_ascii="(^･o･^)ﾉ”"):
        if len(args) > 1 or len(ctx.message.mentions) == 0:
            await ctx.send(embed=simpleEmbed(ctx.author, "Du musst genau eine Person @pingen", color=discord.Color.red()))
        elif ctx.message.mentions[0] == ctx.author:
            await ctx.send(embed=simpleEmbed(ctx.author, "No u", color=discord.Color.red()))
        else:
            e = discord.Embed(title=f"**{ctx.message.mentions[0].display_name}**, du wurdest von **{ctx.author.display_name}** {verb}", description=cat_ascii)
            e.timestamp = datetime.datetime.utcnow()
            e.color = ctx.author.color
            e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)

            gifs = self.readJson(command)
            r = random.randint(0, 25 + len(gifs))
            if r < len(gifs):
                url = random.choice(gifs)
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://purrbot.site/api/img/sfw/{command}/{content_type}") as response:
                        rjson = await response.json()
                        if rjson["error"] == False:
                            url = rjson["link"]
                        else:
                            await ctx.send(embed=simpleEmbed(ctx.author, "Verbindungsfehler zur API", "(´; ω ;｀)", color=discord.Color.red()))
                            return
            e.set_image(url=url)
            await ctx.send(embed=e)
    
    @commands.command()       
    @is_bot_dev()
    async def add(self, ctx, *args):
        """fügt ein GIF für die wholesome-Kategorie hinzu.
        Syntaxbeispiel: `add hug hug_gif.gif`"""

        def is_gif(url):
            try:
                r = requests.head(url)
            except:
                return False
            if r.headers["content-type"] == "image/gif":
                return True
            return False
        if len(args) != 2:
            await ctx.send(embed=simpleEmbed(ctx.author, "Es müssen genau zwei Argumente übergeben werden", "Beispiel: `add hug hug_gif.gif`", color=discord.Color.red()))
            return
        category = args[0]
        if category not in self.cmds:
            await ctx.send(embed=simpleEmbed(ctx.author, "Die angegebene Kategorie ist nicht vorhanden", color=discord.Color.red()))
            return
        gif = args[1]
        if not is_gif(gif):
            await ctx.send(embed=simpleEmbed(ctx.author, "Die angegebene URL ist kein gültiges GIF.", color=discord.Color.red()))
            return
        self.addInJson(category, str(gif))
        await ctx.send(embed=simpleEmbed(ctx.author, "Das GIF wurde erfolgreich zur Kategorie hinzugefügt."))


    def readJson(self, name : str):
        try:
            with open(config.path + f'/json/{name}.json', 'r') as myfile:
                return json.loads(myfile.read())
        except FileNotFoundError:
            return []

    def addInJson(self, name : str, add):
        try:
            js = self.readJson(name)
            with open(config.path + f'/json/{name}.json', 'w') as myfile:
                js.append(add)
                json.dump(js, myfile)
        except FileNotFoundError:
            file = open(config.path + f'/json/{name}.json', 'w')
            file.write("[]")
            file.close()


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


class UserMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self.read_json()

    @commands.Cog.listener()
    async def on_message(self, message):
        js = self.data
        if str(message.author.id) in js.keys():
            if message.content in js[str(message.author.id)].keys():
                await message.channel.send(random.choice(js[str(message.author.id)][message.content]))


    @commands.command(aliases=["am"])
    async def addMessage(self, ctx, *args):
        """Füge eine neue Reaktion auf eine bestimmte Nachricht von dir hinzu.
        Die Syntax ist: `addMessage "deine Nachricht, falls es mehr als ein Wort ist in Hochkommas" "Die Reaktionsnachricht des Bots"`"""
        if len(args) != 2:
            await ctx.send(embed=simpleEmbed(ctx.author, "Du musst genau zwei Argumente angeben",
                        'Die Syntax ist: `addMessage "deine Nachricht, falls es mehr als ein Wort ist in Hochkommas" "Die Reaktionsnachricht des Bots"`',
                        color=discord.Color.red()))
            return
        self.add_in_json(ctx.author, args[0], args[1])
        e = simpleEmbed(ctx.author, "Erfolgreich hinzugefügt!", color=ctx.author.color)
        e.description = f"`{args[1]}` wurde erfolgreich `{args[0]}` hinzugefügt."
        await ctx.send(embed=e)


    @commands.command(aliases=["rm"])
    async def removeMessage(self, ctx, *args):
        """Lösche eine bereits existierende Reaktion auf eine bestimmte Nachricht von dir.
        Die Syntax ist: `removeMessage "Nachricht, die gelöscht werden soll (in Hochkommas, falls mehr als ein Wort)"`"""
        if str(ctx.author.id) in self.data.keys():
            if len(args) != 1:
                await ctx.send(embed=simpleEmbed(ctx.author, "Du musst genau ein Argument angeben",
                            'Die Syntax ist: `removeMessage "Nachricht, die gelöscht werden soll (in Hochkommas, falls mehr als ein Wort)"`',
                            color=discord.Color.red()))
            else:
                if args[0] in self.data[str(ctx.author.id)].keys():
                    self.remove_from_json(ctx.author, args[0])
                    e = simpleEmbed(ctx.author, "Erfolgreich entfernt!", color=ctx.author.color)
                    e.description = f"`{args[0]}` wurde erfolgreich entfernt."
                    await ctx.send(embed=e)
                else:
                    await ctx.send(embed=simpleEmbed(ctx.author, "Diese Nachricht befindet sich nicht in deinen Nachrichten.", color=discord.Color.red()))

        else:
            await ctx.send(embed=simpleEmbed(ctx.author, "Du hast keine eigenen Nachrichten eingestellt.", color=discord.Color.red()))


    @commands.command(aliases=["mm"])
    async def myMessages(self, ctx, *args):
        """Lasse deine eingestellten Nachrichten aufzählen"""
        e = discord.Embed(title="Deine Nachrichten", color=ctx.author.color)
        if str(ctx.author.id) in self.data.keys():
            for k in self.data[str(ctx.author.id)].keys():
                e.add_field(name=str(k), value=str(self.data[str(ctx.author.id)][k]), inline=False)
        else:
            e.description = "Du hast keine eigenen Nachrichten eingestellt."
        await ctx.send(embed=e)
    
    def read_json(self):
        try:
            with open(config.path + f'/json/userReactions.json', 'r') as myfile:
                return json.loads(myfile.read())
        except FileNotFoundError:
            return {}

    def add_in_json(self, user, on_msg, bot_reaction_msg):
        js = self.data
        try:
            with open(config.path + '/json/userReactions.json', 'w') as myfile:
                if not str(user.id) in js.keys():
                    js[str(user.id)] = {}
                if not on_msg in js[str(user.id)].keys():
                    js[str(user.id)][on_msg] = []
                js[str(user.id)][on_msg].append(bot_reaction_msg)
                json.dump(js, myfile)
        except FileNotFoundError:
            file = open(config.path + '/json/userReactions.json', 'w')
            file.write("{}")
            file.close()
            self.add_in_json(user, on_msg, bot_reaction_msg)
        self.data = js

    def remove_from_json(self, user, key):
        js = self.data
        try:
            with open(config.path + '/json/userReactions.json', 'w') as myfile:
                del js[str(user.id)][key]
                json.dump(js, myfile)
        except FileNotFoundError:
            file = open(config.path + '/json/userReactions.json', 'w')
            file.write("{}")
            file.close()
        self.data = js



bot.add_cog(Erinnerungen(bot))
bot.add_cog(Stundenplan(bot))
bot.add_cog(Wholesome(bot))
bot.add_cog(UserMessages(bot))
bot.add_cog(Memes(bot))
bot.add_cog(Utility(bot))
bot.add_cog(Debug(bot))
bot.add_cog(Schulneuigkeiten(bot))

bot.add_cog(Ahmad(bot))


bot.help_command = HelpCommand()

bot.run(config.TOKEN)
