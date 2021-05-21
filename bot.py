import os
import requests
import discord
from discord.ext import commands
from discord import File
from dotenv import load_dotenv
import time
import pandas as pd
from io import StringIO
import asyncio

from tetrioScheme import TetrioScheme
from coloredText import utilStrs
from progress import progressBar



load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

gameSchemes = {
    "tetr.io":TetrioScheme
}

bot = commands.Bot(command_prefix='-tsds ')

@bot.listen('on_ready')
async def on_ready():
    print("Connected to discord")

@bot.command(
    name='seedFromCsv', 
    category="main features",
    help='<game> [-IgnoreChecking] //Seed a file from a csv file either embeding'+\
        'it alongside the command or answering with the command to the embeded file.')
async def seedFromCsv(ctx:commands.Context, game: str = None, checkIn: str = None):
    msg:discord.Message = ctx.message
    checkInBool = True
    if game == None or game == "":
        baseStr = utilStrs.SPECIFY_GAME
        games = getGamesStrDiff()
        await ctx.send(baseStr.format(games))
        return
    elif game not in gameSchemes:
        baseStr = utilStrs.UNEXISTING_GAME
        games = getGamesStrDiff()
        await ctx.send(baseStr.format(game, games))
        return
    if checkIn != "-IgnoreCheckIn":
        checkInBool = False    
    
    try:
        csvs:str = await getCsvTextFromMsg(msg, ctx)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))
        gamesch = gameSchemes[game]
        loop = asyncio.get_event_loop()
        gamescheme = gamesch(ctx, playersDF, loop)
        bar = progressBar(ctx, gamescheme)
        await ctx.send(utilStrs.INFO.format("Retrieving player data..."))
        ret = await asyncio.gather(
            bar.setupProgressBar(),
            gamescheme.retrieveData(checkInBool)
        )
        await ctx.send(utilStrs.INFO.format("Seeding players..."))
        df:pd.DataFrame = ret[1]
        df.sort_values('VS',ascending=False, ignore_index=True, inplace=True)
        df["Seed"] = df.index + 1

        dfcsv = df.to_csv(index=False)

        await ctx.send(
            content=utilStrs.INFO.format("File generated"),
            file= File(fp=StringIO(dfcsv), filename="Seeding.csv")
            )

    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))


async def getCsvTextFromMsg(msg:discord.Message, ctx:commands.Context):
    if msg.attachments:
        file_url = msg.attachments[0]
    elif msg.reference:
        ref_msg = await ctx.fetch_message(msg.reference.message_id)
        if not ref_msg.attachments:
            raise Exception("Did not find any CSV file")
        file_url = ref_msg.attachments[0]
    else:
        raise Exception("Did not find any CSV file")
    req = requests.get(file_url)
    if req.status_code == 200:
        return req.content.decode('utf-8')
    else:
        raise Exception("Could not read CSV file")


def getGamesStrDiff():
    games = ""
    for game in gameSchemes.keys():
        games += "+ "+game+"\n"
    return games


if __name__ == '__main__':
    bot.run(TOKEN)
