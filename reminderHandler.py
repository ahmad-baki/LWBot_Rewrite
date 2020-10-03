import lwConfig
import json
import datetime


def updateReminder(reminder):
    with open(lwConfig.path + '/reminder.json', 'w') as myfile:
        json.dump(reminder, myfile)


def getReminder():
    with open(lwConfig.path + '/reminder.json', 'r') as myfile:
        return json.loads(myfile.read())


def addReminder(author, time, message):
    reminder = getReminder()
    authors = list(reminder.keys())
    if not str(author) in authors:
        reminder[str(author)] = []
    reminder[str(author)].append((time, message))
    updateReminder(reminder)


def removeReminder(author, time, message):
    reminder = getReminder()
    authors = list(reminder.keys())
    if str(author.id) in authors:
        if [time, message] in reminder[str(author.id)]:
            reminder[str(author.id)].pop(
                reminder[str(author.id)].index([time, message]))
    updateReminder(reminder)
