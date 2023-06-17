import discord
from configparser import ConfigParser
from pathlib import Path
import lib as lib



BASE = Path(__file__).resolve().parent
CONFIG = ConfigParser()
CONFIG.read(BASE / 'config.ini')
BOT_KEY = CONFIG.get('discord', 'bot_secret')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    if not hasattr(client, 'appinfo'):
        client.appinfo = await client.application_info()
        print(client.appinfo)
    

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content == '/dm me':
        dm = await client.create_dm(message.author)
        await dm.send('suh duh')

    if message.content == '/latest_chapter swordking':
        newest_update = lib.swordking_latest("swordking")
        await message.channel.send(newest_update)


client.run(BOT_KEY)
