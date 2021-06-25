import asyncio
from baseScheme import BaseScheme

import requests
import discord
from discord.ext import commands

import pandas as pd
from coloredText import utilStrs
import json
import traceback

# input
# "teamName","inGameName","checkedInAt","Tetr.io name","Discord Username (with numbers)"

# output
# Seed, BattlefyName, Name, Discord, TR, Glicko, VS, APM, PPS, Sprint, Blitz, Hours

tetrioRanks = ["z","d","d+"] + [let + sign for let in "cbas" for sign in ["-","","+"]] + ["ss","u",'x']


class TetrioScheme(BaseScheme):
    def __init__(self, ctx:commands.Context, data:pd.DataFrame, loop: asyncio.BaseEventLoop):
        super().__init__(ctx, data, loop)
        self.data.columns = ["teamName","inGameName","checkedInAt","Tetr.io_Name","Discord_Name"]
        self.__apiURL = "https://ch.tetr.io/api/"

    def getOptions(self) -> list:
        return ["-CheckRankUnder","-FilterNoRank"]
    
    def getOptionsHelp(self) -> list:
        return ["-CheckRankUnder=<rank>","-FilterNoRank"]

    async def checkOptions(self, **kwargs):
        checkRank = kwargs.get('-CheckRankUnder', None)
        if checkRank and checkRank not in tetrioRanks:
            await self._BaseScheme__client.close()
            raise Exception( f"The rank '{checkRank}' does not exist. You must type the rank in lower case.")        
        return True

    async def retrieveData(self, **kwargs) -> pd.DataFrame:
        #filter players who's checkin time is NaN
        df = self.data
        ignoreCheckIn = kwargs.get("-IgnoreCheckIn",False)
        if not ignoreCheckIn:
            df = df[df["checkedInAt"] == df["checkedInAt"]].reset_index(drop=True)
        
        checkRank = kwargs.get('-CheckRankUnder', None)

        war = utilStrs.WARNING
        err = utilStrs.ERROR
        
        outPutCols = ['Seed', 'BattlefyName', 'Name', 'Discord', 'TR', 'Glicko', 'VS', 'APM', 'PPS', 'Sprint', 'Blitz']
        retDF = pd.DataFrame(columns=outPutCols)
        #function for async foreach
        async def getPlayerAt(i):
            try:
                player = df.iloc[i]
                playerName:str = player["Tetr.io_Name"]
                ingameName:str = player["teamName"]
                if not playerName or playerName != playerName:
                    await self.context.send(err.format("Error: " + ingameName + " does not have tetr.io name."))
                    return
                playerName:str = self.getPlayerName(playerName).lower()
                
                status1, reqData = await self._BaseScheme__getJson(self.__apiURL + f"users/{playerName}")
                status2, reqRecords = await self._BaseScheme__getJson(self.__apiURL + f"users/{playerName}/records")

                if status1 != 200:
                    await self.context.send(err.format(f"Error {status1}: for tetr.io username '{playerName}'."))
                    return

                # the request was succesful
                playerData = json.loads(reqData.decode('utf-8'))
                playerRecords = json.loads(reqRecords.decode('utf-8'))

                if not playerData["success"]:
                    await self.context.send(err.format(f"Error: '{playerName}' does not exist."))
                    return

                if not playerRecords["success"]:
                    await self.context.send(err.format(f"Error: Could not retrieve records for '{playerName}'"))
                    return

                playerData = playerData["data"]["user"]
                playerRecords = playerRecords["data"]["records"]

                if kwargs.get('-FilterNoRank', False) and playerData["league"]["rank"] == 'z':
                    await self.context.send(err.format(f"Error: '{playerName}' has no rank "))
                    return

                if checkRank:
                    if tetrioRanks.index(playerData["league"]["rank"]) > tetrioRanks.index(checkRank):
                        await self.context.send(err.format(f"Error: '{playerName}' has rank '{playerData['league']['rank']}', higher than '{checkRank}'"))
                        return
                    status3, reqNews = await self._BaseScheme__getJson(self.__apiURL + f"news/user_{playerData['_id']}")
                    playerNews = json.loads(reqNews.decode('utf-8'))
                    if status3 != 200:
                        await self.context.send(err.format(f"Error {status2}: for tetr.io username '{playerName}'."))
                        return
                    if not playerNews["success"]:
                        await self.context.send(err.format(f"Error: Could not retrieve news for '{playerName}'"))
                        return
                    news = playerNews["data"]["news"]
                    for new in news:
                        if new["type"] == "rankup" and tetrioRanks.index(new["data"]["rank"]) > tetrioRanks.index(checkRank):
                            await self.context.send(err.format(f"Error: '{playerName}' has achieved '{new['data']['rank']}', higher than '{checkRank}'"))

                # get and validate rest of needed info
                playerDiscord:str = player["Discord_Name"]
                playerTR:int = round(playerData["league"]["rating"])
                playerGlicko:float = round(playerData["league"].get("glicko", -1))
                playerVS:float = playerData["league"].get("vs", 0.0)
                playerAPM:float = playerData["league"].get("apm", 0.0)
                playerPPS:float = playerData["league"].get("pps", 0.0)

                playerSprint = playerRecords["40l"]["record"]
                playerBlitz = playerRecords["blitz"]["record"]
                
                playerSprint:float = round(playerSprint["endcontext"]["finalTime"],2) if playerSprint is not None else 999999.00
                playerBlitz:float = playerBlitz["endcontext"]["score"] if playerBlitz is not None else 0

                playerRow = [
                    -1, #Seed will be re assigned later
                    ingameName,
                    playerName,
                    playerDiscord,
                    playerTR,
                    playerGlicko,
                    playerVS,
                    playerAPM,
                    playerPPS,
                    playerSprint,
                    playerBlitz
                ]
                retDF.loc[i] = playerRow
            except Exception as e:
                traceback.print_exc()
                await self.context.send(err.format(f"Error: Looks like there was an error for player at row '{i}'"))
            self.progress += 1


        coros = [getPlayerAt(i) for i in range(len(df))]
        await asyncio.gather(*coros)

        self.finished = True
        await self._BaseScheme__client.close()

        return retDF
        
    def getPlayerName(self, name:str) -> str:
        '''This function covers the scenario where instead of inputing the 
        tetr.io username the dumb user inputs the tetra channel link'''
        ret = name
        if "u/" in name:
            i = name.find('u/',1)
            ret = name[i+2:]
        elif "s/" in name:
            i = name.find('s/',1)
            ret = name[i+2:]
        return ret.strip()
