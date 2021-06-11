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
from secTetrioScheme import SecTetrioScheme
from baseScheme import BaseScheme
from coloredText import utilStrs
from progress import progressBar

# TODO implement functionality to sort by any given column

gameSchemes = {
    "tetr.io":TetrioScheme,
    "secuential-tetr.io":SecTetrioScheme
}

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

preffix = '-tsds '
if os.getenv('DEV'):
    preffix = '-tsdev '

bot = commands.Bot(command_prefix=preffix)


@bot.listen('on_ready')
async def on_ready():
    print("Connected to discord")

@bot.command(
    name='getPlayers', 
    category="main features",
    help='getPlayers <game> [-IgnoreCheckIn]\n......Generate a seeding from a csv file either embeding '
        'it alongside the command or answering with the command to the embeded file.')
async def getPlayers(ctx:commands.Context, game: str = None, checkIn: str = None):
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
        print("Ignorando check in")
        checkInBool = False    
    
    try:
        csvs:str = await getCsvTextFromMsg(msg, ctx)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))
        print(len(csvs.split("\n")), " file lines")
        gamesch = gameSchemes[game]
        loop = asyncio.get_event_loop()
        gamescheme:BaseScheme = gamesch(ctx, playersDF, loop)
        bar = progressBar(ctx, gamescheme)
        await ctx.send(utilStrs.INFO.format("Retrieving player data..."))
        ret = await asyncio.gather(
            bar.setupProgressBar(),
            gamescheme.retrieveData(checkInBool)
        )
        await ctx.send(utilStrs.INFO.format("Data retrieved"))
        df:pd.DataFrame = ret[1]

        dfcsv = df.to_csv(index=False)

        await ctx.send(
            content=utilStrs.INFO.format("File generated"),
            file= File(fp=StringIO(dfcsv), filename="Seeding.csv")
            )

    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))

@bot.command(
    name='seedBy',
    help="seedBy <column> [asc|dec]\n......Given a csv file with player data, seed them by a given <column> in ascending or descending order. "
    "If order is not specified the data will be sorted in ascending order."
) #TODO allow for multiple columns
async def seedBy(ctx:commands.Context, col:str, direction:str = None):
    msg:discord.Message = ctx.message
    try:
        csvs:str = await getCsvTextFromMsg(msg, ctx)
        playersDF:pd.DataFrame = pd.read_csv(StringIO(csvs))

        if col not in playersDF.columns:
            await ctx.send(utilStrs.ERROR.format(f"The data does not include the column '{col}'"))
            return

        if direction != None and direction not in ("asc","dec"):
            await ctx.send(utilStrs.ERROR.format(f"For '{col}'"))
            return

        asc = (direction == 'asc') or (direction == None)         

        await ctx.send(utilStrs.INFO.format("Seeding players..."))
        playersDF.sort_values(col, ascending=asc, ignore_index=True, inplace=True)
        playersDF["Seed"] = playersDF.index + 1

        dfcsv = playersDF.to_csv(index=False)
        await ctx.send(
            content=utilStrs.INFO.format("File generated"),
            file= File(fp=StringIO(dfcsv), filename="Seeding.csv")
            )
        
    except Exception as e:
        await ctx.send(utilStrs.ERROR.format(e))
    


bot.remove_command('help')
@bot.command(
    name='help', 
    category="main features",
    help='help [<command>]\n......Display this help message for all commands or just <command> if specified.')
async def sendHelp(ctx:commands.Context, cmd:str = None):
    if cmd:
        if cmd in [c.name for c in bot.commands]:
            c:commands.Command = bot.get_command(cmd)
            await ctx.send(utilStrs.DIFF.format(f"+ {c.help}"))
        else:
            cmdstr = "".join([f"+ {c.name}\n" for c in bot.commands])
            await ctx.send(utilStrs.UNEXISTING_COMMAND.format(cmd,cmdstr))
    else:
        cmdstr = "".join([f"+ {c.help}\n\n" for c in bot.commands])
        await ctx.send(utilStrs.DIFF.format(cmdstr))


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
