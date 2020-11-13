import lwConfig
import json
import datetime


def updateReminder(reminder):
    with open(lwConfig.path + '/json/reminder.json', 'w') as myfile:
        json.dump(reminder, myfile)


def getReminder():
    with open(lwConfig.path + '/json/reminder.json', 'r') as myfile:
        return json.loads(myfile.read())


def addReminder(author, recipient, time, message):
    reminder = getReminder()
    recipients = list(reminder.keys())
    if not str(recipient) in recipients:
        reminder[str(recipient)] = []
    reminder[str(recipient)].append([time, message, author])
    updateReminder(reminder)


def removeReminder(recipientID, time, message, author):
    reminder = getReminder()
    recipients = list(reminder.keys())
    if str(recipientID) in recipients:
        if [time, message, author] in reminder[str(recipientID)]:
            reminder[str(recipientID)].pop(reminder[str(recipientID)].index([time, message, author]))
    updateReminder(reminder)
