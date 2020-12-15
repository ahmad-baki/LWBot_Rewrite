import lwConfig
import json
from bs4 import BeautifulSoup
import aiohttp
import asyncio
from datetime import datetime
from jsondiff import diff, insert, delete
import base64
import gzip

def getMyCourseRoles(ctxAuthor):
    kurse = []
    # all course roles except the @everyone role
    for r in ctxAuthor.roles[1:len(ctxAuthor.roles)]:
        if lwConfig.courseRoleSeperatorID != r.id:
            kurse.append(r)
        else:
            break
    return kurse


def getMyCourseRoleNames(ctx):
    return [c.name for c in getMyCourseRoles(ctx)]


async def createCourseRole(ctx, name):
    await ctx.guild.create_role(name=name)


def updateSubstitutionPlan(substitutionPlan):
    with open(lwConfig.path + '/json/substitutionPlan.json', 'w') as myfile:
        json.dump(substitutionPlan, myfile)


def getSubstitutionPlan():
    with open(lwConfig.path + '/json/substitutionPlan.json', 'r') as myfile:
        return json.loads(myfile.read())

async def get_plan_urls(username, password):
    date_string = datetime.now().strftime("%Y-%m-%dT%H:%M:%S:%f0")

    data = json.dumps({
        "AppId": "2092d12c-8470-4ef8-8c70-584965f9ffe5",
        "UserId": username,
        "UserPw": password,
        "AppVersion": "2.5.9",  # latest in PlayStore since 2016/02/18
        "Device": "VirtualBox",
        "OsVersion": "27 8.1.0",
        "Language": "de",
        "Date": date_string,
        "LastUpdate": date_string,
        "BundleId": "de.heinekingmedia.dsbmobile"
    }, separators=(",", ":")).encode("utf-8")

    body = {
        "req": {
            # data is sent gzip compressed and base64 encoded
            "Data": base64.b64encode(gzip.compress(data)).decode("utf-8"),
            "DataType": 1
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post("https://app.dsbcontrol.de/JsonHandler.ashx/GetData", json=body) as response:
            rjson = await response.json()
            response_data = json.loads(gzip.decompress(
                base64.b64decode(rjson["d"])).decode("utf-8"))
            for result in response_data['ResultMenuItems']:
                if result['Title'] != 'Inhalte':
                    continue
                for child in result['Childs']:
                    if child['MethodName'] != 'timetable':
                        continue
                    for child2 in child['Root']['Childs']:
                        if child2['Title'] != 'Schüler mobil':
                            continue
                        return list(map(lambda plan: plan['Detail'], child2['Childs']))
            return []

async def getCurrentSubstitutionPlan():
    async def get_only_grade_n(iterable, n):
        list_of_items_to_remove = []
        # geht die Liste durch, und schaut, welche einträge nicht zur n. Klasse gehören und merkt sich diese
        for element in iterable[0: len(iterable) - 1][0]:
            if(element["Klasse"] != n):
                list_of_items_to_remove.append(element)
        # löscht die elemente, welche er sich gemerkt hat
        for element in list_of_items_to_remove:
            iterable[0].remove(element)
        return iterable


    async def extract_table_from_site(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200:
                    soup = BeautifulSoup(await r.text(), "html.parser")
                    table_odd = soup.find_all("tr", class_="list odd")
                    table_even = soup.find_all("tr", class_="list even")
                    rows = []
                    for line in table_odd:
                        kurs = zeile_to_Dict(line.find_all("td", class_="list"))
                        rows.append(kurs)
                    for line in table_even:
                        kurs = zeile_to_Dict(line.find_all("td", class_="list"))
                        rows.append(kurs)
                    date = soup.find("div", class_="mon_title")
                    if(date == None):
                        date = "11.11.2011 kein Datum vorhanden [Fehler]"
                    else:
                        date = date.text
                    return (rows, date)


    def zeile_to_Dict(zeile):
        kurs = {}
        kurs["Klasse"] = zeile[0].text
        kurs["Stunde"] = zeile[1].text
        kurs["Art"] = zeile[6].text
        kurs["altes_Fach"] = zeile[2].text
        kurs["neues_Fach"] = zeile[4].text
        kurs["Vertreter"] = zeile[3].text.replace("+", "-")
        kurs["Raum"] = zeile[5].text.replace("---","-")
        kurs["Bemerkungen"] = zeile[7].text
        return kurs

    currentPlan = getSubstitutionPlan()
    try:
        url1,url2,url3 = (await get_plan_urls(lwConfig.subPlanUsername, lwConfig.subPlanPassword))
    except ValueError:
        return (currentPlan, currentPlan)
    

    # remove everything and get the newest substitution plan data

    newPlan = {}
    table1, date1 = await get_only_grade_n(await extract_table_from_site(url1), "12")
    table2, date2 = await get_only_grade_n(await extract_table_from_site(url2), "12")
    table3, date3 = await get_only_grade_n(await extract_table_from_site(url3), "12")
    newPlan[date1] = table1
    newPlan[date2] = table2
    newPlan[date3] = table3
    
    updateSubstitutionPlan(newPlan)
    return (currentPlan, newPlan)

def format_plan(plan, guild, embed, courses=[]):
    if courses == []:
        courses = getMyCourseRoleNames(guild)
    for date in list(plan.keys()):
        substitutions = []
        for i in range(len(plan[date])):
            field = plan[date][i]
            if field["altes_Fach"] in courses:
                course = field["altes_Fach"]
            elif field["neues_Fach"] in courses:
                course = field["neues_Fach"]
            else:
                continue
            if course in courses:
                substitutions.append(field)

        # get the max field length for all substitutions
        length = [0, 0, 0, 0, 0, 0]
        for i in range(len(substitutions)):
            # j is the length index
            j = 0
            for k in list(substitutions[i].keys()):
                if k == "altes_Fach":
                    if substitutions[i]["altes_Fach"] in courses:
                        substitutions[i][k] = substitutions[i]["altes_Fach"]
                    elif substitutions[i]["neues_Fach"] in courses:
                        substitutions[i][k] = substitutions[i]["neues_Fach"]
                elif k == "neues_Fach" or k == "Klasse":
                    continue

                length[j] = max(length[j], len(substitutions[i][k]))
                j += 1
            
        # sort substitutions by time of lesson
        substitutions = sorted(
            substitutions, key=lambda k: k['Stunde'].split()[0])

        # stretch strings and apply them to the result string
        result = ""
        for i in range(len(substitutions)):
            # j is the length index
            j = 0
            result += "`"
            for k in list(substitutions[i].keys()):
                if k == "neues_Fach" or k == "Klasse":
                    continue
                # stretch the strings if needed
                substitutions[i][k] = substitutions[i][k].ljust(length[j])
                j += 1
                result += substitutions[i][k] + ("" if k == (list(substitutions[i].keys())[
                                                len(substitutions[i].keys()) - 1]) else "  ")
            result += f"`\n`{'-'*(sum(length) + 10)}`\n"
            if(len(result) > 1000):
                # date += " [zu viele Vertretungen]"
                embed.add_field(name=date, value=result[:1000] + "`", inline=False)
                result = "`" + result[1000:]

        if result.strip().replace("`", "") != "":
            # if(len(result) > 1020):
            #     result = result[:1020] + "..."
            #     date += " [zu viele Vertretungen]"
            embed.add_field(name=date, value=result, inline=False)
    return embed