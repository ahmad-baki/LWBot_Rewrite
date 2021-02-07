import json
from os import scandir
import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
from discord.ext import tasks

import config
from bot import on_command_error


class Anzeige():
    def __init__(self, price=None, time=None, id=None, location=None, title=None, description=None, url=None):
        self.price = price
        self.time = time
        self.id = id
        self.location = location
        self.title = title
        self.description = description
        self.url = url


def get_ads(config):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36 Edg/84.0.522.59'
    }
    r = requests.get(url=f'{config["url"]}r{config["radius"]}', headers=headers)
    soup = BeautifulSoup(r.text, features="html5lib")
    results = soup.find("div", id="srchrslt-content")
    ads = []
    for i in results.find_all("article"):
        ad = Anzeige()
        ad.id = i["data-adid"]
        details = i.find("div", {"class": "aditem-details"})
        ad.price = details.find("strong").text
        radius = details.contents[8].split()[-2:]
        if int(radius[0]) > config["radius"]:
            continue
        ad.location = f"{details.contents[4].split()[-1]} {details.contents[6].split()[-1]} ({' '.join(radius)})"
        ad.description = i.find(
            "div", {"class": "aditem-main"}).contents[3].contents[0]
        ad.time = ' '.join(
            i.find("div", {"class": "aditem-addon"}).contents[0].split())

        title = i.find("a", {"class": "ellipsis"})
        ad.title = title.contents[0]
        ad.url = config["base_url"] + title["href"]
        ads.append(ad)
    return ads


def ad_to_embed(ad: Anzeige):
    e = discord.Embed(title=ad.title)
    e.description = ad.description
    e.url = ad.url
    e.add_field(name="Preis", value=ad.price)
    e.add_field(name="Ort", value=ad.location)
    e.set_footer(text=ad.time)
    e.color = discord.Color.dark_red()
    return e


class Scraper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.id = 272455097496240130
        self.config = {
            "url": "https://www.ebay-kleinanzeigen.de/s-mainz/anzeige:angebote/macbook-air-m1/k0l5315",
            "base_url": "https://www.ebay-kleinanzeigen.de",
            "radius": 150
        }
        self.scraper.start()

    @tasks.loop(seconds=300)
    async def scraper(self):
        ads = get_ads(self.config)
        with open(config.path + '/json/user_config.json', 'r') as myfile:
            data = json.loads(myfile.read())

        if str(self.id) not in data.keys():
            data[str(self.id)] = {}
            data[str(self.id)]["ids"] = []

        for ad in ads:
            if ad.id not in data[str(self.id)]["ids"]:
                data[str(self.id)]["ids"].append(ad.id)
                channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
                await channel.send(embed=ad_to_embed(ad), content=self.bot.get_user(self.id).mention)

        with open(config.path + '/json/user_config.json', 'w') as myfile:
            json.dump(data, myfile)

    @scraper.before_loop
    async def beforeReminderCheck(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Scraper(bot))
