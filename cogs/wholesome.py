import discord
from discord.ext import commands

import datetime
import json
import random
import aiohttp
import requests

import config
from helper_functions import *
from bot import is_bot_dev

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
            await ctx.send(embed=simple_embed(ctx.author, "Du musst genau eine Person @pingen", color=discord.Color.red()))
        elif ctx.message.mentions[0] == ctx.author:
            await ctx.send(embed=simple_embed(ctx.author, "No u", color=discord.Color.red()))
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
                            await ctx.send(embed=simple_embed(ctx.author, "Verbindungsfehler zur API", "(´; ω ;｀)", color=discord.Color.red()))
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
            await ctx.send(embed=simple_embed(ctx.author, "Es müssen genau zwei Argumente übergeben werden", "Beispiel: `add hug hug_gif.gif`", color=discord.Color.red()))
            return
        category = args[0]
        if category not in self.cmds:
            await ctx.send(embed=simple_embed(ctx.author, "Die angegebene Kategorie ist nicht vorhanden", color=discord.Color.red()))
            return
        gif = args[1]
        if not is_gif(gif):
            await ctx.send(embed=simple_embed(ctx.author, "Die angegebene URL ist kein gültiges GIF.", color=discord.Color.red()))
            return
        self.addInJson(category, str(gif))
        await ctx.send(embed=simple_embed(ctx.author, "Das GIF wurde erfolgreich zur Kategorie hinzugefügt."))


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

def setup(bot):
    bot.add_cog(Wholesome(bot))