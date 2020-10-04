'''
https://discord.com/api/oauth2/authorize?bot_id=760125323580276757&permissions=8&scope=bot
'''

from asyncio import futures
import discord
from discord.ext import commands
from discord.ext import tasks
from discord.ext.commands.errors import CommandNotFound, NotOwner
from discord.ext.commands.errors import MissingRequiredArgument

import traceback
import asyncio
import datetime
import operator
import os

import lwConfig
import lwHelperFunctions
import voteListHandler
import reminderHandler
import substitutionHandler

bot = commands.Bot(command_prefix=lwConfig.prefix)
bot.owner_ids = lwConfig.ownerID


@bot.event
async def on_error(event, *args, **kwargs):
    embed = discord.Embed(title=f'new Error in event {event}()')
    embed.color = discord.Color.red()
    embed.description = f"```{traceback.format_exc()}```"
    embed.set_footer(text=kwargs)
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    error = getattr(error, 'original', error)
    if isinstance(error, CommandNotFound) or isinstance(error, MissingRequiredArgument):
        return
    if isinstance(error, NotOwner):
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Du hast keine Berechtigung diesen Command auszuführen.", color=discord.Color.red()))
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
        type=discord.ActivityType.watching, name=lwConfig.statusMessage)
    await bot.change_presence(activity=activity, status=discord.enums.Status.dnd)
    e = discord.Embed(title="Bot started")
    e.color = discord.Color.blurple()
    e.timestamp = datetime.datetime.utcnow()
    e.set_footer(text=bot.user.name, icon_url=bot.user.avatar_url)
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=e)


@bot.listen()
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id == lwConfig.memeChannelID and len(message.attachments) > 0:
        await message.add_reaction(lwHelperFunctions.getEmoji(bot, lwConfig.upvoteEmoji))
        await message.add_reaction(lwHelperFunctions.getEmoji(bot, lwConfig.downoteEmoji))
    if message.content.startswith("awoo"):
        await test(ctx=message, arg=message.content)


@bot.command(name="eval", aliases=["ev", "evaluate"])
async def _eval(ctx, *, arg):
    if await bot.is_owner(ctx.author):
        try:
            await eval(arg, {
                "ctx": ctx,
                "bot": bot,
                "lwHelperFunctions": lwHelperFunctions,
                "discord": discord,
                "datetime": datetime,
                "reminderHandler": reminderHandler,
                "os": os
            })
        except Exception as e:
            if isinstance(e, TypeError):
                pass
            else:
                raise e
    else:
        awoo = lwHelperFunctions.getEmoji(bot, "AwOo")
        e = discord.Embed(title="You are not worthy ")
        e.set_image(url=awoo.url)
        e.color = discord.Color.blurple()
        e.timestamp = datetime.datetime.utcnow()
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=e)


@bot.command()
async def embed(ctx, *args):
    await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, *args))


@bot.command()
async def test(ctx, *, arg):
    e = discord.Embed(title="testing stuffu")
    e.color = discord.Color.blurple()
    e.description = arg
    e.timestamp = datetime.datetime.utcnow()
    e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
    await ctx.send(embed=e)


@bot.command()
async def emotes(ctx):
    e = discord.Embed(title="Emotes:")
    emotes = [f"<:{e.name}:{e.id}>" for e in bot.emojis]
    e.description = ''.join(emotes)
    e.timestamp = datetime.datetime.utcnow()
    e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
    m = await ctx.send(embed=e)
    # for i in range(min(20, len(emotes))):
    #    await m.add_reaction(emotes[i])


@bot.command()
async def entries(ctx):
    voteListHandler.deleteOldMessages()
    voteList = voteListHandler.getVoteList()
    e = discord.Embed()
    e.color = discord.Color.purple()
    e.timestamp = datetime.datetime.utcnow()
    e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
    e.set_author(name=bot.user, icon_url=bot.user.avatar_url)
    if not len(voteList) > 0:
        e.title = "No entries in the votelist."
        await ctx.send(embed=e)
        return
    e.title = "Entries"
    e.description = "All current entry messages in the votelist.\n\n```[ MessageID:\n Upvotes \u2606, created_at ]```"
    for k in list(voteList.keys()):
        e.add_field(
            name=f"{str(k)}:", value=f"```{str(voteList[k][0])} \u2606, {str(voteList[k][1])}```", inline=False)

    await ctx.send(embed=e)


@bot.command()
async def stats(ctx):
    async with ctx.message.channel.typing():
        voteListHandler.deleteOldMessages()
    voteList = voteListHandler.getVoteList()
    if(len(voteList) > 0):
        vList = {}
        for i in voteList.keys():
            vList[i] = voteList[i][0]
        sortedDict = sorted(
            vList.items(), key=operator.itemgetter(1), reverse=True)
        winnerMessage = await bot.get_channel(lwConfig.memeChannelID).fetch_message(sortedDict[0][0])
        score = voteList[sortedDict[0][0]][0]
        e = discord.Embed()
        e.title = f"Current top voted post with a score of {str(score)} {lwHelperFunctions.getEmoji(bot, lwConfig.upvoteEmoji)}"

        e.description = winnerMessage.content
        e.set_image(url=winnerMessage.attachments[0].url)
        e.set_author(name=winnerMessage.author,
                     icon_url=winnerMessage.author.avatar_url)
        e.color = winnerMessage.guild.get_member(
            winnerMessage.author.id).colour
        date = winnerMessage.created_at
        e.description += f"\n`Message created at:  {str(date).split('.')[0]}`"
        e.timestamp = datetime.datetime.utcnow()
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.message.channel.send(embed=e)
        if(not lwHelperFunctions.is_url_image(e.image.url)):
            await ctx.message.channel.send(winnerMessage.attachments[0].url)
    else:
        await ctx.message.channel.send("no items in the voting list.")


@bot.command(aliases=["remindme"])
async def reminder(ctx, *, arg):
    try:
        time = datetime.datetime.strptime(arg, '%d.%m.%Y %H:%M')
        if time < datetime.datetime.now():
            await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Reminder in the past?", "not allowed.", color=discord.Color.orange()))
            return
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Please enter a message for the reminder", "Dont answer for 60 seconds to time out.", color=discord.Color.gold()))
        m = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
    except ValueError:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Wrong date format.", "your Date should be in the format\n```reminder dd.mm.yyyy hh:mm\nExample: reminder 1.10.2020 6:34```", color=discord.Color.red()))
        return
    except futures.TimeoutError:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Timed out.", "Try again if you want to set a reminder.", color=discord.Color.red()))
        return
    except Exception:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Some Error occured", "Your reminder could not be set.", color=discord.Color.red()))
    else:
        reminderHandler.addReminder(ctx.author.id, arg, m.content)
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "new reminder set for " + arg, m.content))
        return


@bot.command(aliases=["mr"])
async def myreminders(ctx):
    reminder = reminderHandler.getReminder()
    if str(ctx.author.id) in list(reminder.keys()) and len(reminder[str(ctx.author.id)]) > 0:
        e = discord.Embed(title="Your Reminders", color=ctx.author.color,
                          timestamp=datetime.datetime.utcnow())
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        for singleReminder in reminder[str(ctx.author.id)]:
            e.add_field(name=singleReminder[0],
                        value=singleReminder[1], inline=False)
        await ctx.send(embed=e)
    else:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "You have no reminders.", f"Type {bot.command_prefix}reminder [date] to create one."))


@bot.command(aliases=["rmr"])
async def removereminder(ctx):
    reminder = reminderHandler.getReminder()
    if str(ctx.author.id) in list(reminder.keys()) or len(reminder[str(ctx.author.id)]) == 0:
        e = discord.Embed(title="Your Reminders", color=ctx.author.color,
                          timestamp=datetime.datetime.utcnow())
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)
        reminderCount = len(reminder[str(ctx.author.id)])
        for i in range(reminderCount):
            singleReminder = reminder[str(ctx.author.id)][i]
            e.add_field(name=f"[{i}] {singleReminder[0]}",
                        value=singleReminder[1], inline=False)
        await ctx.send(embed=e)
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Please enter a index to remove", "Dont answer for 60 seconds to time out.", color=discord.Color.gold()))
        try:
            m = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
            index = int(m.content)
            if 0 <= index < reminderCount:
                reminderHandler.removeReminder(
                    ctx.author.id, *reminder[str(ctx.author.id)][index])
                await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Reminder removed.", f"Your reminder\n```{reminder[str(ctx.author.id)][index][1]}``` was removed."))
            else:
                raise ValueError
        except futures.TimeoutError:
            await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Timed out.", "Try again if you want to remove a reminder.", color=discord.Color.red()))
        except ValueError:
            await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "ValueError", "Your message was not a number or the number is not in the indices.", color=discord.Color.red()))
    else:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "You have no reminders.", f"Type {bot.command_prefix}reminder [date] to create one."))


@bot.command()
async def kurse(ctx):
    if not lwConfig.courseRoleSeperatorID in [c.id for c in substitutionHandler.getMyCourseRoles(ctx.author)]:
        await ctx.author.add_roles(ctx.guild.get_role(lwConfig.courseRoleSeperatorID))
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Du hast keine Kurse ausgewählt. ", "Verwende den command addKurse [kurs1 kurs2 ...] um mehr hinzuzufügen.\nBeispiel: ```addKurse EN4 PH1```\ngibt dir die Kursrollen EN4 und PH1."))
        return
    kurse = substitutionHandler.getMyCourseRoleNames(ctx.author)
    if len(kurse) > 0:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Deine Kurse: ", f"```{', '.join(kurse)}```"))
    else:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Du hast keine Kurse ausgewählt. ", "Verwende den command addKurse [kurs1 kurs2 ...] um mehr hinzuzufügen.\nBeispiel: ```addKurse EN4 PH1```\ngibt dir die Kursrollen EN4 und PH1."))
        

@bot.command(aliases=["ak"])
async def addKurse(ctx, *, args):
    args = args.split(" ")
    if not lwConfig.courseRoleSeperatorID in [c.id for c in substitutionHandler.getMyCourseRoles(ctx.author)]:
        await ctx.author.add_roles(ctx.guild.get_role(lwConfig.courseRoleSeperatorID))
    for arg in args:
        if arg not in substitutionHandler.getMyCourseRoleNames(ctx.guild):
            await substitutionHandler.createCourseRole(ctx, arg)
        if arg not in substitutionHandler.getMyCourseRoleNames(ctx.author):
            roleID = [r.id for r in substitutionHandler.getMyCourseRoles(
                ctx.author) if r.name == arg]
            await ctx.author.add_roles(ctx.guild.get_role(roleID))

    kurse = substitutionHandler.getMyCourseRoleNames(ctx.author)
    await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Deine Kurse: ", f"```{', '.join(kurse)}```"))


# @bot.command()
# @commands.is_owner()
# async def addKurs(ctx, *args):
#     for arg in args:
#         if arg not in substitutionHandler.getCourseRoleNames(ctx):
#             await substitutionHandler.createCourseRole(ctx, arg)
#         else:
#             await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, f"Eine Rolle für den Kurs {arg} existiert bereits.", color=discord.Color.red()))
#     kurse = substitutionHandler.getCourseRoleNames(ctx)
#     await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Die Kurse: ", ', '.join(kurse)))

@bot.listen()
async def on_raw_reaction_add(payload):
    # check if the channel of the reaction is the specified channel
    if payload.channel_id != lwConfig.memeChannelID:
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
    upvote = lwHelperFunctions.getEmoji(bot, lwConfig.upvoteEmoji)
    downvote = lwHelperFunctions.getEmoji(bot, lwConfig.downoteEmoji)
    if user != bot.user:
        # in case the message author tries to up-/downvote their own post
        if reaction.message.author == user and (reaction.emoji == upvote or reaction.emoji == downvote):
            await reaction.remove(user)
            errormsg = await reaction.message.channel.send(f"{user.mention} you cannot up/downvote your own post.")
            deleteEmoji = lwHelperFunctions.getEmoji(
                bot, lwConfig.deleteEmojiName)
            await errormsg.add_reaction(deleteEmoji)
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == user and _reaction.emoji.name == deleteEmoji.name)
            except futures.TimeoutError:
                pass
            await errormsg.delete()
            return

        # change voting counter
        if reaction.emoji == upvote:
            voteListHandler.changeVotingCounter(reaction.message, 1)
            # pin message when it has the specified amount of upvotes
            if reaction.count - 1 >= lwConfig.upvotesForPin and not reaction.message.pinned:
                await reaction.message.pin(reason="good meme")
        elif reaction.emoji == downvote:
            voteListHandler.changeVotingCounter(reaction.message, -1)


@bot.listen()
async def on_raw_reaction_remove(payload):
    # check if the channel of the reaction is the specified channel
    if payload.channel_id != lwConfig.memeChannelID:
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
        if reaction.emoji == lwHelperFunctions.getEmoji(bot, lwConfig.upvoteEmoji):
            voteListHandler.changeVotingCounter(reaction.message, -1)
        elif reaction.emoji == lwHelperFunctions.getEmoji(bot, lwConfig.downoteEmoji):
            voteListHandler.changeVotingCounter(reaction.message, 1)


@bot.listen()
async def on_voice_state_update(member, before, after):
    afkChannel = member.guild.afk_channel
    if after.channel and before.channel:  # if the member didn't just join or quit, but moved channels
        if after.channel == afkChannel and before.channel.id in lwConfig.awakeChannelIDs:
            await member.move_to(before.channel)


@tasks.loop(seconds=30)
async def checkReminder():
    r = reminderHandler.getReminder()
    now = datetime.datetime.now()
    authors = list(r.keys())
    for authorID in authors:
        for reminder in r[authorID]:
            time = datetime.datetime.strptime(reminder[0], '%d.%m.%Y %H:%M')
            if time <= now:
                channel = bot.get_channel(lwConfig.botChannelID)
                author = bot.get_guild(
                    lwConfig.serverID).get_member(int(authorID))
                color = author.color
                await channel.send(content=author.mention, embed=lwHelperFunctions.simpleEmbed(author, "Reminder", reminder[1], color=color))
                reminderHandler.removeReminder(authorID, *reminder)


@tasks.loop(seconds=300)
async def checkGmoWebsite():
    news = await lwHelperFunctions.getGmoNews()
    if news != None:
        channel = bot.get_channel(lwConfig.newsChannelID)
        await channel.send(channel.guild.get_role(lwConfig.gmoRoleID).mention + " " + news)


@checkGmoWebsite.before_loop
async def beforeGmoNews():
    await bot.wait_until_ready()
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "gmoNewsCheck loop start", color=discord.Color.green()))


@checkGmoWebsite.after_loop
async def afterGmoNews():
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "gmoNewsCheck loop stopped. restarting now", color=discord.Color.orange()))
    checkGmoWebsite.restart()


@checkReminder.before_loop
async def beforeReminderCheck():
    await bot.wait_until_ready()
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "reminder loop start", color=discord.Color.green()))


@checkReminder.after_loop
async def afterReminderCheck():
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "reminder loop stopped. restarting now", color=discord.Color.orange()))
    checkGmoWebsite.restart()

checkGmoWebsite.start()
checkReminder.start()
bot.run(lwConfig.token)
