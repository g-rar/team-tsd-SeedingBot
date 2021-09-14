import os
from typing import Tuple
import requests
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import pandas as pd
from io import StringIO
import aiohttp
from coloredText import utilStrs as strs
import json

class BaseScheme:
    def __init__(self, ctx:commands.Context, data:pd.DataFrame,loop:asyncio.BaseEventLoop):
        super().__init__()
        self.context = ctx
        self.data:pd.DataFrame = data
        self.progress = 0
        self.finished = False
        self.__client = aiohttp.ClientSession(loop=loop)

    async def retrieveData(self, **kwargs) -> Tuple[pd.DataFrame]:
        raise NotImplementedError

    def seedPlayers(self,players:pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    async def checkOptions(self, **kwargs) -> bool:
        '''If something with the given options is not right, raises an exception and may send feedback msg.'''
        raise NotImplementedError

    def getOptions(self, optDict) -> list:
        raise NotImplementedError

    async def __getJson(self, url):
        async with self.__client.get(url) as response:
            res = (await response.read()).decode('utf-8')
            try:
                return (response.status, json.loads(res))
            except json.JSONDecodeError:
                return (response.status, {"error":"jsonDecodeError", "headers": response.headers})
