import discord
import lwConfig
from bs4 import BeautifulSoup
import aiohttp
import importlib
import json
import requests

def getEmoji(bot, emojiName):
    emoji = discord.utils.get(bot.emojis, name=emojiName)
    if emoji:
        return emoji
    return None

async def getGmoNews():
    global LATEST_GMO_NEWS_NUMBER
    url = "https://www.gymnasium-oberstadt.de/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                soup = BeautifulSoup(await r.text(), "html.parser")
                for link in soup.findAll('a'):
                    if str(link.get('href')).startswith('https://www.gymnasium-oberstadt.de/neuigkeiten/'):
                        number = int(str(link.get('href')).replace('https://www.gymnasium-oberstadt.de/neuigkeiten/', "").split(".")[0])
                        if number > lwConfig.latestGmoNewsNumber:
                            lwConfig.config["latest_gmo_news_number"] = number
                            with open(lwConfig.path + '/lwConfig.json', 'w') as myfile:
                                myfile.write(json.dumps(lwConfig.config)) 
                            updateConfig()
                            return str(link.get('href'))
    return None

def updateConfig():
    importlib.reload(lwConfig)

def is_url_image(image_url):
    image_formats = ("image/png", "image/jpeg", "image/jpg", "image/gif")
    r = requests.head(image_url)
    if r.headers["content-type"] in image_formats:
        return True
    return False