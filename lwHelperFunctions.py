import discord
import lwConfig
from bs4 import BeautifulSoup
import aiohttp
import importlib
import json
import requests
import datetime

def getEmoji(bot, emojiName):
    emoji = discord.utils.get(bot.emojis, name=emojiName)
    if emoji:
        return emoji
    return None

async def getGmoNews():
    url = "https://www.gymnasium-oberstadt.de/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                soup = BeautifulSoup(await r.text(), "html.parser")
                for link in soup.findAll('a'):
                    if str(link.get('href')).startswith('https://www.gymnasium-oberstadt.de/neuigkeiten/'):
                        number = int(str(link.get('href')).replace('https://www.gymnasium-oberstadt.de/neuigkeiten/', "").split(".")[0])
                        if number > lwConfig.latest_news_number:
                            lwConfig.config["latest_gmo_news_number"] = number
                            with open(lwConfig.path + '/json/lwConfig.json', 'w') as myfile:
                                myfile.write(json.dumps(lwConfig.config)) 
                            updateConfig()
                            return str(link.get('href'))
    return None

def updateConfig():
    importlib.reload(lwConfig)

def is_url_image(image_url):
    image_formats = ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp")
    try:
        r = requests.head(image_url)
        if r.headers["content-type"] in image_formats:
            return True
        return False
    except:
        return False

def simpleEmbed(author, title, description = "", image_url="", color=discord.Color.blurple()):
    e = discord.Embed(title=title, description=description)
    if image_url != "":
        e.set_image(url=image_url)
    e.color = color
    e.timestamp = datetime.datetime.utcnow()
    e.set_footer(text=author.name, icon_url=author.avatar_url) 
    return e