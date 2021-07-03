import asyncio
from baseScheme import BaseScheme

import requests
import discord
from discord.ext import commands

import pandas as pd
from coloredText import utilStrs
import json
import traceback

class JstrisScheme(BaseScheme):
    def __init__(self, ctx, data, loop):
        super().__init__(ctx, data, loop)
        self.data.columns = ["teamName","inGameName","checkedInAt","JStris_Profile","Discord_Name"]
        self.__apiURL = "https://jstris.jezevec10.com/api/"

    #TODO perhaps add filters for specific modes
    def getOptions(self) -> list:
        return []
    
    def getOptionsHelp(self) -> list:
        return []

    async def checkOptions(self, **kwargs):
        return True
    
    async def retrieveData(self, **kwargs):
        df = self.data
        ignoreCheckIn = kwargs.get("-IgnoreCheckIn",False)
        if not ignoreCheckIn:
            df = df[df["checkedInAt"] == df["checkedInAt"]].reset_index(drop=True)

        war = utilStrs.WARNING
        err = utilStrs.ERROR
        
        outPutCols = ['Seed', 'BattlefyName', 'Name', 'Discord', 
            'Sprint40L', 
            # 'Ultra'
        ]
        retDF = pd.DataFrame(columns=outPutCols)
        errorDF = pd.DataFrame(columns=df.columns)
        # async def getPlayerAt(i, t):
        for i in range(len(df)):
            try:
                # await asyncio.sleep(t*4)
                player = df.iloc[i]
                playerName = player["JStris_Profile"]
                playerName = self.getPlayerName(playerName)
                
                sprintResCode,sprintData = await self.getWithCoolDown(self.__apiURL + f"u/{playerName}/records/1?mode=1") #get 40l records
                if sprintResCode != 200 or "error" in sprintData:
                    await self.context.send(err.format(f"Could not find sprint data for '{playerName}'"))
                    errorDF.loc[i] = player
                    continue
                
                # ultraResCode, ultraData = await self.getWithCoolDown(self.__apiURL + f"u/{playerName}/records/5?mode=1") #get ultra records
                # if ultraResCode != 200 or "error" in ultraData:
                #     await self.context.send(err.format(f"Could not find ultra data for '{playerName}'"))
                #     errorDF.loc[i] = player
                #     continue
                
                sprintPB = sprintData["min"]
                # ultraPB = ultraData['max']
                battlefyName = player["teamName"]
                playerDiscord = player["Discord_Name"]

                playerRow = [
                    -1, #Seed will be added afterwards
                    battlefyName,
                    playerName,
                    playerDiscord,
                    sprintPB,
                    # ultraPB
                ]
                retDF.loc[i] = playerRow
            except Exception as e:
                traceback.print_exc()
                await self.context.send(err.format(f"Error: Looks like there was an error for player at row '{i}'"))
            self.progress += 1

        # coros = [getPlayerAt(i, i%5) for i in range(len(df))]
        # await asyncio.gather(*coros)
        self.finished = True
        await self._BaseScheme__client.close()
        return retDF

    async def getWithCoolDown(self, url):
        code, data = await self._BaseScheme__getJson(url)
        while code == 429: #too many requests
            await asyncio.sleep(7)
            code, data = await self._BaseScheme__getJson(url)
        return code, data

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