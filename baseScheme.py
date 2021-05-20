import os
import requests
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import pandas as pd
from io import StringIO
import aiohttp
from coloredText import utilStrs as strs

class BaseScheme:
    def __init__(self, ctx:commands.Context, data:pd.DataFrame,loop:asyncio.BaseEventLoop):
        super().__init__()
        self.context = ctx
        self.data:pd.DataFrame = data
        self.progress = 0
        self.finished = False
        self.__apiURL = "https://ch.tetr.io/api/"
        self.__client = aiohttp.ClientSession(loop=loop)

    async def processData(self,ignoreCheckIn:bool):
        raise NotImplementedError
    
    async def __getJson(self, url):
        async with self.__client.get(url) as response:
            return (response.status, await response.read())