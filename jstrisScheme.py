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
        
        outPutCols = ['Seed', 'BattlefyName', 'Name', 'Discord', 'TR', 'Glicko', 'VS', 'APM', 'PPS', 'Sprint', 'Blitz']
        retDF = pd.DataFrame(columns=outPutCols)
        async def getPlayerAt(i):
            try:
                pass
            except Exception as e:
                traceback.print_exc()
                await self.context.send(err.format(f"Error: Looks like there was an error for player at row '{i}'"))
            self.progress += 1

        coros = [getPlayerAt(i) for i in range(len(df))]
        await asyncio.gather(*coros)
        self.finished = True
        await self._BaseScheme__client.close()
        return retDF


        return super().retrieveData(**kwargs)