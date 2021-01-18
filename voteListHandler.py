import lwConfig
import json
import datetime


def updateVoteListFile(voteList):
    with open(lwConfig.path + '/json/voteList.json', 'w') as myfile:
        json.dump(voteList, myfile)


def getVoteList():
    with open(lwConfig.path + '/json/voteList.json', 'r') as myfile:
        return json.loads(myfile.read())


def changeVotingCounter(message, amountToChange):
    voteList = getVoteList()
    if not str(message.id) in list(voteList.keys()):
        voteList[str(message.id)] = (amountToChange, str(message.created_at))
        updateVoteListFile(voteList)
        return
    voteList[str(message.id)] = (voteList[str(message.id)][0] +
                                 amountToChange, voteList[str(message.id)][1])
    updateVoteListFile(voteList)


def deleteOldMessages():
    voteList = getVoteList()
    keys = list(voteList.keys())
    timeNow = datetime.datetime.today()
    for messageID in keys:
        try:
            days = (timeNow - datetime.datetime.strptime(voteList[messageID][1], '%Y-%m-%d %H:%M:%S.%f')).days
        except ValueError:
            days = (timeNow - datetime.datetime.strptime(voteList[messageID][1], '%Y-%m-%d %H:%M:%S')).days
        if days > lwConfig.DELETE_AFTER_DAYS:
            if messageID in keys:
                voteList.pop(messageID)

    updateVoteListFile(voteList)
