import asyncio
from baseScheme import BaseScheme

import requests
import discord
from discord.ext import commands

import pandas as pd
from coloredText import utilStrs
import logging
import re
import traceback
from urllib.parse import quote_plus as urlFormat

# input
# "teamName","inGameName","checkedInAt","Tetr.io name","Discord Username (with numbers)"

# output
# Seed, TeamName, Name, Discord, TR, Glicko, VS, APM, PPS, Sprint, Blitz, Hours

tetrioRanks = ["z","d","d+"] + [let + sign for let in "cbas" for sign in ["-","","+"]] + ["ss","u",'x']
tetrioNamePttr = (
    r"(?=^[a-z0-9\-_]{3,16}$)" # length of 3-16, only a-z, 0-9, dash and underscore
    r"(?=^(?!guest-.*$).*)"    # does not start with guest-
    r"(?=.*[a-z0-9].*)"        # has a letter or number somewhere
)

class OverUnderScheme(BaseScheme):
    def __init__(self, ctx:commands.Context, data:pd.DataFrame, loop: asyncio.BaseEventLoop):
        super().__init__(ctx, data, loop)
        self.data.columns = ["teamName","inGameName","checkedInAt","OverTetrioTag","OverDiscordTag", "UnderTetrioTag", "UnderDiscordTag"]
        self.__apiURL = "https://ch.tetr.io/api/"

    def getOptions(self) -> list:
        return ["-RemoveOver","RemoveUnder","-FilterNoRank"]
    
    def getOptionsHelp(self) -> list:
        return ["-RemoveOver=<rank>","-RemoveUnder=<rank>","-FilterNoRank"]

    async def checkOptions(self, **kwargs):
        checkRank = kwargs.get('-OverTop', None)
        if checkRank and checkRank not in tetrioRanks:
            await self._BaseScheme__client.close()
            raise Exception( f"The rank '{checkRank}' does not exist. You must type the rank in lower case.")        
        checkRank = kwargs.get('-OverBottom', None)
        if checkRank and checkRank not in tetrioRanks:
            await self._BaseScheme__client.close()
            raise Exception( f"The rank '{checkRank}' does not exist. You must type the rank in lower case.")        
        checkRank = kwargs.get('-UnderTop', None)
        if checkRank and checkRank not in tetrioRanks:
            await self._BaseScheme__client.close()
            raise Exception( f"The rank '{checkRank}' does not exist. You must type the rank in lower case.")        
        checkRank = kwargs.get('-UnderBottom', None)
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

        df.drop_duplicates(subset="teamName", inplace=True, ignore_index=True)
        
        overTop = kwargs.get('-OverTop', None)
        overBottom = kwargs.get('-OverBottom', None)
        underTop = kwargs.get('-UnderTop', None)
        underBottom = kwargs.get('-UnderBottom', None)

        war = utilStrs.WARNING
        err = utilStrs.ERROR
        
        outPutCols = ['TeamName', 
                        'OverName', 'OverDiscord', 'OverTR', 'OverGlicko', 'OverVS', 'OverAPM', 'OverPPS', 'OverSprint', 'OverBlitz',
                        'UnderName', 'UnderDiscord', 'UnderTR', 'UnderGlicko', 'UnderVS', 'UnderAPM', 'UnderPPS', 'UnderSprint', 'UnderBlitz',
                        'AvgVS', 'OverWeightedVS']
        retDF = pd.DataFrame(columns= ["Seed"] + outPutCols)
        errorDF = pd.DataFrame(columns= outPutCols + ["Error"])
        #function for async foreach
        async def getPlayerAt(i):
            try:
                player = df.iloc[i]
                teamName:str = player["teamName"]
                overName:str = player["OverTetrioTag"]

                # ---------------------- Check name exists
                if not overName or overName != overName:
                    errorDF.loc[i] = {"TeamName":teamName, "Error": "Over player Does not have tetr.io name"}
                    self.progress += 1
                    return

                underName:str = player["UnderTetrioTag"]
                if not underName or underName != underName:
                    errorDF.loc[i] = {"TeamName":teamName, "Error": "Under player Does not have tetr.io name"}
                    self.progress += 1
                    return
                
                overName:str = self.getPlayerName(overName).lower()
                underName:str = self.getPlayerName(underName).lower()

                # ---------------------- Check name is valid
                if not re.match(tetrioNamePttr, overName):
                    errorDF.loc[i] = {"TeamName":teamName, "Name":overName, "Error": f"Invalid Over tetrio username"}
                    self.progress += 1
                    return
                if not re.match(tetrioNamePttr, underName):
                    errorDF.loc[i] = {"TeamName":teamName, "Name":underName, "Error": f"Invalid Under tetrio username"}
                    self.progress += 1
                    return

                # ---------------------- Check data retrieval for over
                status1, overData = await self._BaseScheme__getJson(self.__apiURL + f"users/{overName}")
                status2, overRecords = await self._BaseScheme__getJson(self.__apiURL + f"users/{overName}/records")

                if status1 != 200:
                    errorDF.loc[i] = {"TeamName":teamName, "Name":overName, "Error": f"Error {status1}"}
                    self.progress += 1
                    return

                # the request was not succesful
                if not overData["success"]:
                    errorDF.loc[i] = {"TeamName":teamName, "Name":overName, "Error": "Player does not exist."}
                    self.progress += 1
                    return

                if not overRecords["success"]:
                    errorDF.loc[i] = {"TeamName":teamName, "Name":overName, "Error": "Could not retrieve records"}
                    self.progress += 1
                    return

                # ---------------------- Check data retrieval for under
                status1, underData = await self._BaseScheme__getJson(self.__apiURL + f"users/{underName}")
                status2, underRecords = await self._BaseScheme__getJson(self.__apiURL + f"users/{underName}/records")

                if status1 != 200:
                    errorDF.loc[i] = {"TeamName":teamName, "Name":underName, "Error": f"Error {status1}"}
                    self.progress += 1
                    return

                # the request was not succesful
                if not underData["success"]:
                    errorDF.loc[i] = {"TeamName":teamName, "Name":underName, "Error": "Player does not exist."}
                    self.progress += 1
                    return

                if not underRecords["success"]:
                    errorDF.loc[i] = {"TeamName":teamName, "Name":underName, "Error": "Could not retrieve records"}
                    self.progress += 1
                    return

                # ---------------------- Fill row
                overData = overData["data"]["user"]
                overRecords = overRecords["data"]["records"]
                overDiscord:str = player["OverDiscordTag"]
                overTR:int = round(overData["league"]["rating"])
                overGlicko:float = round(overData["league"].get("glicko", -1))
                overVS:float = overData["league"].get("vs", 0.0)
                overAPM:float = overData["league"].get("apm", 0.0)
                overPPS:float = overData["league"].get("pps", 0.0)
                overSprint = overRecords["40l"]["record"]
                overBlitz = overRecords["blitz"]["record"]                
                overSprint:float = round(overSprint["endcontext"]["finalTime"],2) if overSprint is not None else 999999.00
                overBlitz:float = overBlitz["endcontext"]["score"] if overBlitz is not None else 0

                underData = underData["data"]["user"]
                underRecords = underRecords["data"]["records"]
                underDiscord:str = player["UnderDiscordTag"]
                underTR:int = round(underData["league"]["rating"])
                underGlicko:float = round(underData["league"].get("glicko", -1))
                underVS:float = underData["league"].get("vs", 0.0)
                underAPM:float = underData["league"].get("apm", 0.0)
                underPPS:float = underData["league"].get("pps", 0.0)
                underSprint = underRecords["40l"]["record"]
                underBlitz = underRecords["blitz"]["record"]
                underSprint:float = round(underSprint["endcontext"]["finalTime"],2) if underSprint is not None else 999999.00
                underBlitz:float = underBlitz["endcontext"]["score"] if underBlitz is not None else 0

                playerRow = [
                    -1, #Seed will be re assigned later
                    teamName,
                    overName,
                    overDiscord,
                    overTR,
                    overGlicko,
                    overVS,
                    overAPM,
                    overPPS,
                    overSprint,
                    overBlitz,
                    underName,
                    underDiscord,
                    underTR,
                    underGlicko,
                    underVS,
                    underAPM,
                    underPPS,
                    underSprint,
                    underBlitz,
                    round((overVS + underVS)/2,3),
                    round((2*overVS + underVS)/3,3),
                ]

                # ---------------------- Validate over
                if kwargs.get('-FilterNoRank', False) and overData["league"]["rank"] == 'z':
                    errorDF.loc[i] = playerRow[1:] + ["Over has no rank"]
                    return

                if overTop or overBottom:
                    # check ceiling against current rank 
                    achievedOverBottom = False
                    if overTop and tetrioRanks.index(overData["league"]["rank"]) > tetrioRanks.index(overTop):
                        errorDF.loc[i] = playerRow[1:] + [f"Over Has rank '{overData['league']['rank']}'>'{overTop}'"]
                        self.progress += 1
                        return
                    # get news to see previous rankUps
                    status3, playerNews = await self._BaseScheme__getJson(self.__apiURL + f"news/user_{overData['_id']}")
                    if status3 != 200:
                        errorDF.loc[i] = playerRow[1:] + [f"Error {status3}"]
                        self.progress += 1
                        return
                    if not playerNews["success"]:
                        errorDF.loc[i] = playerRow[1:] + ["Could not retrieve news for Over"]
                        self.progress += 1
                        return
                    news = playerNews["data"]["news"]
                    # check against previous ranks
                    for new in news:
                        if overTop and new["type"] == "rankup" and tetrioRanks.index(new["data"]["rank"]) > tetrioRanks.index(overTop):
                            errorDF.loc[i] = playerRow[1:] + [f"Over has achieved '{new['data']['rank']}'>'{overTop}'"]
                            self.progress += 1
                            return
                        if overBottom and new["type"] == "rankup" and tetrioRanks.index(new["data"]["rank"]) >= tetrioRanks.index(overBottom):
                            achievedOverBottom = True
                    # check bottom, if achieved over bottom player is included
                    if overBottom and not achievedOverBottom and tetrioRanks.index(overData["league"]["rank"]) < tetrioRanks.index(overBottom):
                        errorDF.loc[i] = playerRow[1:] + [f"Over Has rank '{overData['league']['rank']}'<'{overBottom}'"]
                        self.progress += 1
                        return
                
                
                # ---------------------- Validate under
                if kwargs.get('-FilterNoRank', False) and underData["league"]["rank"] == 'z':
                    errorDF.loc[i] = playerRow[1:] + ["Under has no rank"]
                    return

                if underTop or underBottom:
                    # check ceiling against current rank 
                    achievedUnderBottom = False
                    if underTop and tetrioRanks.index(underData["league"]["rank"]) > tetrioRanks.index(underTop):
                        errorDF.loc[i] = playerRow[1:] + [f"Under Has rank '{underData['league']['rank']}'>'{underTop}'"]
                        self.progress += 1
                        return
                    # get news to see previous rankUps
                    status3, playerNews = await self._BaseScheme__getJson(self.__apiURL + f"news/user_{underData['_id']}")
                    if status3 != 200:
                        errorDF.loc[i] = playerRow[1:] + [f"Error {status3}"]
                        self.progress += 1
                        return
                    if not playerNews["success"]:
                        errorDF.loc[i] = playerRow[1:] + ["Could not retrieve news for Under"]
                        self.progress += 1
                        return
                    news = playerNews["data"]["news"]
                    # check against previous ranks
                    for new in news:
                        if underTop and new["type"] == "rankup" and tetrioRanks.index(new["data"]["rank"]) > tetrioRanks.index(underTop):
                            errorDF.loc[i] = playerRow[1:] + [f"Under has achieved '{new['data']['rank']}'>'{underTop}'"]
                            self.progress += 1
                            return
                        if underBottom and new["type"] == "rankup" and tetrioRanks.index(new["data"]["rank"]) >= tetrioRanks.index(underBottom):
                            achievedUnderBottom = True
                    # check bottom, if achieved under bottom player is included
                    if underBottom and not achievedUnderBottom and tetrioRanks.index(underData["league"]["rank"]) < tetrioRanks.index(underBottom):
                        errorDF.loc[i] = playerRow[1:] + [f"Under Has rank '{underData['league']['rank']}'<'{underBottom}'"]
                        self.progress += 1
                        return

                retDF.loc[i] = playerRow
            except Exception as e:
                logging.error(f"At row {i} --\n {traceback.format_exc()}")
                errorDF.loc[i] = {"TeamName":teamName, "Name":overName, "Error": f"Unknown Error, row {i}"}
            self.progress += 1


        coros = [getPlayerAt(i) for i in range(len(df))]
        await asyncio.gather(*coros)

        self.finished = True
        await self._BaseScheme__client.close()

        return (retDF, errorDF)
        
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
