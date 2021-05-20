import asyncio
from baseScheme import BaseScheme

import requests
import discord
from discord.ext import commands

import pandas as pd
from coloredText import utilStrs
import json

# input
# "teamName","inGameName","checkedInAt","Tetr.io name","Discord Username (with numbers)"

# output
# Seed, BattlefyName, Name, Discord, TR, Glicko, VS, APM, PPS, Sprint, Blitz, Hours

class TetrioScheme(BaseScheme):
    def __init__(self, ctx:commands.Context, data:pd.DataFrame, loop: asyncio.BaseEventLoop):
        super().__init__(ctx, data, loop)
        self.data.columns = ["teamName","inGameName","checkedInAt","Tetr.io_Name","Discord_Name"]
        self.__apiURL = "https://ch.tetr.io/api/"
    
    async def retrieveData(self,ignoreCheckIn:bool):
        #filter players who's checkin time is None
        df = self.data
        if not ignoreCheckIn:
            df = df[df["checkedInAt"] == df["checkedInAt"]].reset_index(drop=True)
        
        war = utilStrs.WARNING
        err = utilStrs.ERROR
        
        outPutCols = ['Seed', 'BattlefyName', 'Name', 'Discord', 'TR', 'Glicko', 'VS', 'APM', 'PPS', 'Sprint', 'Blitz']
        retDF = pd.DataFrame(columns=outPutCols)
        
        for i in range(len(df)):
            player = df.iloc[i]
            playerName:str = self.getPlayerName(player["Tetr.io_Name"])
            ingameName:str = player["teamName"]
            if not playerName:
                await self.context.send(err.format("Error: " + ingameName + " does not have tetr.io name."))
                continue
            playerName:str = playerName.lower()
            
            status1, reqData = await self._BaseScheme__getJson(self.__apiURL + f"users/{playerName}")
            status2, reqRecords = await self._BaseScheme__getJson(self.__apiURL + f"users/{playerName}/records")

            if status1 != 200:
                await self.context.send(err.format(f"Error {status1}: for tetr.io username '{playerName}'."))
                continue
            if status2 != 200:
                await self.context.send(err.format(f"Error {status2}: for tetr.io username '{playerName}'."))
                continue

            # the request was succesful
            playerData = json.loads(reqData.decode('utf-8'))
            playerRecords = json.loads(reqRecords.decode('utf-8'))

            if not playerData["success"]:
                await self.context.send(err.format(f"Error: '{playerName}' does not exist."))
                continue

            if not playerData["success"]:
                await self.context.send(err.format(f"Error: Could not retrieve records for '{playerName}'"))
                continue

            playerData = playerData["data"]["user"]
            playerRecords = playerRecords["data"]["records"]

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
            self.progress = i+1
        self.finished = True
        self._BaseScheme__client.close()

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
        return ret


            

