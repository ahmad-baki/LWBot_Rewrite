'''
https://discord.com/api/oauth2/authorize?bot_id=760125323580276757&permissions=8&scope=bot
'''

from asyncio import futures
import discord
from discord.ext import commands
from discord.ext import tasks
from discord.errors import HTTPException
from discord.ext.commands.errors import CommandNotFound, NotOwner
from discord.ext.commands.errors import MissingRequiredArgument

import traceback
import asyncio
import datetime
import operator
import os
import subprocess
import validators
import ast
import json
from collections import defaultdict

import lwConfig
import lwHelperFunctions
import voteListHandler
import reminderHandler
import substitutionHandler

intents = discord.Intents.all()
intents.messages = True
intents.presences = True
bot = commands.Bot(command_prefix=lwConfig.prefix, intents=intents)
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
    if message.channel.id == lwConfig.memeChannelID and (len(message.attachments) > 0 or validators.url(message.content)):
        await message.add_reaction(lwHelperFunctions.getEmoji(bot, lwConfig.upvoteEmoji))
        await message.add_reaction(lwHelperFunctions.getEmoji(bot, lwConfig.downoteEmoji))
    if message.content.startswith("awoo"):
        await test(ctx=message, arg=message.content)


# geklaut https://gist.github.com/nitros12/2c3c265813121492655bc95aa54da6b9
@commands.is_owner()
@bot.command(name="eval", aliases=["ev", "evaluate"])
async def _eval(ctx, *, cmd):
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


@bot.command()
async def embed(ctx, *args):
    await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, *args))


@bot.command()
async def test(ctx, *, arg):
    await bot.fetch_user(int(arg))
    e = discord.Embed(title="testing stuffu")
    e.color = discord.Color.blurple()
    e.description = "ok"  # str([m.name for m in bot.get_all_members()])
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
async def top(ctx):
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

        e.description = f"[Message:]({winnerMessage.jump_url})"
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
            if(not lwHelperFunctions.is_url_image(e.image.url)):
                await ctx.message.channel.send(winnerMessage.attachments[0].url)
    else:
        await ctx.message.channel.send("no items in the voting list.")


@bot.command()
async def stats(ctx, *args):
    if len(args) > 0:
        if not args[0].isnumeric() and len(ctx.message.mentions) == 0:
            return
    progressEmbed = discord.Embed(title="Nachrichten werden gelesen...")
    progressEmbed.description = "Dies könnte (wird) eine recht lange Zeit in Anspruch nehmen."
    progressEmbed.set_image(url=lwHelperFunctions.getEmoji(bot, "KannaSip").url)
    await ctx.send(embed=progressEmbed)
    progress = 0
    progressMsg = await ctx.send("`  0% fertig.`")
    async with ctx.channel.typing():
        channel = bot.get_channel(lwConfig.memeChannelID)
        upvote = lwHelperFunctions.getEmoji(bot, lwConfig.upvoteEmoji)
        downvote = lwHelperFunctions.getEmoji(bot, lwConfig.downoteEmoji)
        members = defaultdict(lambda : defaultdict(int))
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

    
        e = discord.Embed(title="Stats", color=ctx.author.color, timestamp=datetime.datetime.utcnow())
        e.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar_url)

        for member_id in members.keys():
            if len(ctx.message.mentions) > 0:
                if member_id not in [u.id for u in ctx.message.mentions]:
                    continue
            if members[member_id] == {}:
                continue
            if members[member_id]["memes"] == 0:
                continue
            member = bot.get_guild(lwConfig.serverID).get_member(member_id)
            up = members[member_id]['up']
            down = members[member_id]['down']
            total = members[member_id]['memes']
            ratio = round(up / down, 2) if down > 0 else up if up > 0 else 1
            dvratio = "1" if down > 0 else "0"
            members[member_id]["ratio"] = ratio
            e.add_field(name=member.display_name, value=
                f"total memes: `{members[member_id]['memes']}`\n"+
                f"total {str(upvote)} `{str(up).rjust(6)} : {str(down).ljust(6)}` {str(downvote)}\n"+
                f"ratio {str(upvote)} `{str(ratio).rjust(6)} : {dvratio.ljust(6)}` {str(downvote)}\n"+
                f"avg . {str(upvote)} `{str(round(up / total, 2)).rjust(6)} : {str(round(down / total, 2)).ljust(6)}` {str(downvote)}",
                inline=False
            )

        for m in ctx.message.mentions:
            if m.id not in members.keys():
                e.add_field(name=m.display_name, value=
                    "total memes: 0"+
                    f"total {str(upvote)} `     0 : 0     ` {str(downvote)}\n"+
                    f"ratio {str(upvote)} `     1 : 1     ` {str(downvote)}\n"+
                    f"avg.  {str(upvote)} `     0 : 0     ` {str(downvote)}"
                    ,inline=False
                )
    await ctx.send(embed=e)

    ## Leaderboard ##
    l = discord.Embed(title="Leaderboard (upvote/downvote ratio)", color=discord.Color.gold(), timestamp=datetime.datetime.utcnow())

    ratioLeaderboard = []

    for k in members.keys():
        ratioLeaderboard.append([members[k]["ratio"], k])

    ratioLeaderboard.sort(reverse=True)

    for r in ratioLeaderboard:
        member = bot.get_guild(lwConfig.serverID).get_member(r[1])
        l.add_field(name=member.display_name, value=str(r[0]))
    
    await ctx.send(embed=l)

    







@bot.command(aliases=["remindme", "remind", "reminder"])
async def setreminder(ctx, *, arg):
    try:
        length = min(len(arg.split()), 2)
        time_str = ' '.join(arg.split()[:length])
        time = datetime.datetime.strptime(time_str, '%d.%m.%Y %H:%M')
        if time < datetime.datetime.now():
            await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Reminder in the past?", "not allowed.", color=discord.Color.orange()))
            return
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Please enter a message for the reminder", "Dont answer for 60 seconds to time out.", color=discord.Color.gold()))
        m = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
    except ValueError:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Wrong date format.", "your Date should be in the format\n```reminder (d)d.(m)m.yyyy (h)h:(m)m\nExample: reminder 1.10.2020 6:34```", color=discord.Color.red()))
        return
    except futures.TimeoutError:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Timed out.", "Try again if you want to set a reminder.", color=discord.Color.red()))
        return
    except Exception:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Some Error occured", "Your reminder could not be set.", color=discord.Color.red()))
    else:
        if len(ctx.message.mentions) > 0:
            for recipient in ctx.message.mentions:
                reminderHandler.addReminder(
                    ctx.author.id, recipient.id, time_str, m.content + f"\n_created [here]({ctx.message.jump_url})_")
                await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "new reminder set for " + recipient.name + " at " + time_str, m.content))
        else:
            reminderHandler.addReminder(
                ctx.author.id, ctx.author.id, time_str, m.content + f"\n_created [here]({ctx.message.jump_url})_")
            await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "new reminder set for you at " + time_str, m.content))
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
    # give the ctx.author the course seperator role if he does not have it already
    if not lwConfig.courseRoleSeperatorID in [c.id for c in ctx.author.roles]:
        await ctx.author.add_roles(ctx.guild.get_role(lwConfig.courseRoleSeperatorID))
    # if the ctx.author has at least one course role, send it
    kurse = substitutionHandler.getMyCourseRoleNames(ctx.author)
    if len(kurse) > 0:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Deine Kurse: ", f"```{', '.join(kurse)}```"))
    # otherwise, inform the ctx.author that he does not have any course roles
    else:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Du hast keine Kurse ausgewählt. ", "Verwende den command addKurse [kurs1 kurs2 ...] um mehr hinzuzufügen.\nBeispiel: ```addKurse EN4 PH1```\ngibt dir die Kursrollen EN4 und PH1."))


@bot.command(aliases=["ak"])
async def addKurse(ctx, *, args):
    args = args.split(" ")
    # give the ctx.author the course seperator role if he does not have it already
    if not lwConfig.courseRoleSeperatorID in [c.id for c in ctx.author.roles]:
        await ctx.author.add_roles(ctx.guild.get_role(lwConfig.courseRoleSeperatorID))
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
    await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Deine Kurse: ", f"```{', '.join(kurse)}```"))


@bot.command(aliases=["rk"])
async def removeKurse(ctx, *, args):
    args = args.split(" ")
    # give the ctx.author the course seperator role if he does not have it already
    if not lwConfig.courseRoleSeperatorID in [c.id for c in ctx.author.roles]:
        await ctx.author.add_roles(ctx.guild.get_role(lwConfig.courseRoleSeperatorID))
    for arg in args:
        # check if the ctx.author has the role that he wants to remove
        if arg not in substitutionHandler.getMyCourseRoleNames(ctx.author):
            await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Du besitzt diese Kursrolle nicht.", color=discord.Color.red()))
            return
        # get the role id by name
        roleID = [r.id for r in substitutionHandler.getMyCourseRoles(
            ctx.guild) if r.name == arg][0]
        # get the role by the id
        role = ctx.guild.get_role(roleID)
        await ctx.author.remove_roles(role)
        # delete the role if no members have it now
        if len(role.members) == 0:
            await role.delete(reason="not used anymore")
    await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, f"Die Rolle(n) {', '.join(args)} wurde erfolgreich entfernt."))


@bot.command(aliases=["mp"])
async def myplan(ctx):
    # give the ctx.author the course seperator role if he does not have it already
    if not lwConfig.courseRoleSeperatorID in [c.id for c in ctx.author.roles]:
        await ctx.author.add_roles(ctx.guild.get_role(lwConfig.courseRoleSeperatorID))
    # if the ctx.author has at least no course role, tell him and return
    kurse = substitutionHandler.getMyCourseRoleNames(ctx.author)
    if len(kurse) == 0:
        await ctx.send(embed=lwHelperFunctions.simpleEmbed(ctx.author, "Du hast keine Kurse ausgewählt. ", "Verwende den command addKurse [kurs1 kurs2 ...] um mehr hinzuzufügen.\nBeispiel: ```addKurse EN4 PH1```\ngibt dir die Kursrollen EN4 und PH1."))
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
            if reaction.count - 1 >= lwConfig.upvotesForPin:
                # await reaction.message.pin(reason="good meme")
                await sendGoodMeme(reaction.message)
        elif reaction.emoji == downvote:
            voteListHandler.changeVotingCounter(reaction.message, -1)


async def sendGoodMeme(msg):
    with open(lwConfig.path + '/json/goodMemes.json', 'r') as myfile:
        memes = json.loads(myfile.read())

    if msg.id in memes:
        return

    memes.append(msg.id)
    with open(lwConfig.path + '/json/goodMemes.json', 'w') as myfile:
        json.dump(memes, myfile)


    channel = bot.get_channel(lwConfig.goodMemesChannelID)
    e = discord.Embed()
    e.description = f"[Message:]({msg.jump_url})"
    if(len(msg.attachments) > 0):
        e.set_image(url=msg.attachments[0].url)
        counter = 0
        while e.image.width == 0 or counter == 100 and not lwHelperFunctions.is_url_image(e.image.url):
            counter += 1
            e.set_image(url=msg.attachments[0].url)
        if counter == 100:
            await on_command_error(bot.get_channel(lwConfig.logChannelID), Exception(f"{str(msg.id)}: good meme was not sent correctly."))
        elif counter > 0:
            await on_command_error(bot.get_channel(lwConfig.logChannelID), Exception(f"{str(msg.id)}: good meme was not sent correctly, took {counter} attempts."))

    e.set_author(name=msg.author,
                    icon_url=msg.author.avatar_url)
    e.color = msg.guild.get_member(
        msg.author.id).colour
    e.description += "\n" + msg.content
    e.timestamp = msg.created_at
    e.set_footer(text=msg.author.name, icon_url=msg.author.avatar_url)
    await channel.send(embed=e)
    if(len(msg.attachments) > 0):
        if(not lwHelperFunctions.is_url_image(e.image.url)):
            await channel.send(msg.attachments[0].url)
    


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
        if after.channel == afkChannel and before.channel.id in lwConfig.awakeChannelIDs:   #the "Stay awake" feature
            await member.move_to(before.channel)

    if after.channel and member.guild.get_role(lwConfig.banishedRoleID) in member.roles and after.channel.id != lwConfig.banishedChannelD and member.id not in bot.owner_ids:  #the "banish" feature
        await member.move_to(member.guild.get_channel(lwConfig.banishedChannelD))


@bot.listen()
async def on_member_update(before, after):
    # move to hell if banished role was added
    hell = before.guild.get_channel(lwConfig.banishedChannelD)
    r = before.guild.get_role(lwConfig.banishedRoleID)
    if r in after.roles and r not in before.roles and before.id not in bot.owner_ids:
        if after.voice != None:
            if after.voice.channel != hell:
                await after.move_to(hell)


@tasks.loop(seconds=30)
async def checkReminder():
    r = reminderHandler.getReminder()
    now = datetime.datetime.now()
    recipients = list(r.keys())
    for recipientID in recipients:
        for reminder in r[recipientID]:
            time = datetime.datetime.strptime(reminder[0], '%d.%m.%Y %H:%M')
            if time <= now:
                channel = bot.get_channel(lwConfig.botChannelID)
                author = bot.get_guild(
                    lwConfig.serverID).get_member(int(reminder[2]))
                recipient = bot.get_guild(
                    lwConfig.serverID).get_member(int(recipientID))
                color = recipient.color
                await channel.send(content=recipient.mention, embed=lwHelperFunctions.simpleEmbed(author, "Reminder", reminder[1], color=color))
                reminderHandler.removeReminder(recipientID, *reminder)


@tasks.loop(seconds=300)
async def checkGmoWebsite():
    news = await lwHelperFunctions.getGmoNews()
    if news != None:
        channel = bot.get_channel(lwConfig.newsChannelID)
        await channel.send(channel.guild.get_role(lwConfig.gmoRoleID).mention + " " + news)


@tasks.loop(seconds=300)
async def updateSubstitutionPlan():
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
        channel = bot.get_channel(lwConfig.substitutionChannelID)

        rmEmbed = discord.Embed(title="Entfernt", color=discord.Color.red())
        addedEmbed = discord.Embed(title="Neu hinzugefügt", color=discord.Color.green())
        rmEmbed.description = "gelöschte Vertretungen [BETA]"
        addedEmbed.description = "geänderte Vertretungen [BETA]"
        server = channel.guild
        rmEmbed.timestamp = datetime.datetime.utcnow()
        addedEmbed.timestamp = datetime.datetime.utcnow()
        rmEmbed = substitutionHandler.format_plan(removals, server, rmEmbed)
        addedEmbed = substitutionHandler.format_plan(additions, server, addedEmbed)

        if len(rmEmbed.fields) > 0: 
            await channel.send(embed=rmEmbed)
        if len(addedEmbed.fields) > 0:
            await channel.send(embed=addedEmbed)
    except Exception as e:
        try:
            await on_command_error(bot.get_channel(lwConfig.logChannelID), e)
        except Exception:
            pass


@updateSubstitutionPlan.before_loop
async def beforeSubstitutionPlan():
    await bot.wait_until_ready()
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "Vertretungplan loop start", color=discord.Color.green()))

@updateSubstitutionPlan.after_loop
async def afterSubstitutionPlan():
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "Vertretungplan loop stopped.", color=discord.Color.orange()))
    await asyncio.sleep(60)
    updateSubstitutionPlan.restart()

@updateSubstitutionPlan.error
async def substitutionPlanError(error):
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "substitution plan error", color=discord.Color.orange()))
    await on_command_error(bot.get_channel(lwConfig.logChannelID), error)



@checkGmoWebsite.before_loop
async def beforeGmoNews():
    await bot.wait_until_ready()
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "gmoNewsCheck loop start", color=discord.Color.green()))

@checkGmoWebsite.after_loop
async def afterGmoNews():
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "gmoNewsCheck loop stopped.", color=discord.Color.orange()))
    await asyncio.sleep(60)
    checkGmoWebsite.restart()

@checkGmoWebsite.error
async def gmoNewsError(error):
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "gmo news error", color=discord.Color.orange()))
    await on_command_error(bot.get_channel(lwConfig.logChannelID), error)



@checkReminder.before_loop
async def beforeReminderCheck():
    await bot.wait_until_ready()
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "reminder loop start", color=discord.Color.green()))

@checkReminder.after_loop
async def afterReminderCheck():
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "reminder loop stopped.", color=discord.Color.orange()))
    await asyncio.sleep(60)
    checkReminder.restart()

@checkReminder.error
async def ReminderCheckError(error):
    channel = bot.get_channel(lwConfig.logChannelID)
    await channel.send(embed=lwHelperFunctions.simpleEmbed(bot.user, "reminder error", color=discord.Color.orange()))
    await on_command_error(bot.get_channel(lwConfig.logChannelID), error)




# Ahmads Herrschaft

@bot.listen()
async def on_guild_update(before, after):
    if after.id == 693062821650497597:
        if after.name != "Ahmad-Kult":
            await after.edit(name="Ahmad-Kult")

updateSubstitutionPlan.start()
checkGmoWebsite.start()
checkReminder.start()
bot.run(lwConfig.token)
