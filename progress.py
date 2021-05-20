import asyncio
from baseScheme import BaseScheme

import requests
import discord
from discord.ext import commands

import pandas as pd
from coloredText import utilStrs as strs

class progressBar:
    def __init__(self, ctx:commands.Context, sch:BaseScheme):
        super().__init__()
        self.context = ctx
        self.scheme = sch
        self.updateRate = 2
    
    async def setupProgressBar(self):
        l = 60
        maxProg = len(self.scheme.data)
        msg:discord.Message = await self.context.send(strs.INFO.format('-'*l))
        prevP = 0
        while not self.scheme.finished:
            await asyncio.sleep(self.updateRate)
            p = int(l * (self.scheme.progress / maxProg))
            if prevP == p:
                continue
            prevP = p
            pstr = '■'*p
            vstr = '-'*(l-p)
            await msg.edit(content=strs.INFO.format(pstr + vstr))
        