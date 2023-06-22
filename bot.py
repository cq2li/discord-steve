import discord
from configparser import ConfigParser
from pathlib import Path
import lib as lib
import threading
import lib
import asyncio
import logging

BASE = Path(__file__).resolve().parent
CONFIG = ConfigParser()
CONFIG.read(BASE / 'config.ini')
BOT_KEY = CONFIG.get('discord', 'bot_secret')
CHANNEL_OWNER = CONFIG.get('discord', 'channel_owner')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
help_text = """
1. '/refresh' to manually refresh the database of chapters
2. '/latest' and '/last_checked' to request the latest chapter and last scrape time
3. '/dm me' for good times😉

"""

async def send_msg(channel, msg):
    await channel.send("@everyone")
    await channel.send("hi")
    await channel.send(msg)

@client.event
async def on_ready():
    logging.info(f'We have logged in as {client.user}')
    if not hasattr(client, 'appinfo'):
        client.appinfo = await client.application_info()
        # print(client.appinfo)
    for gd in client.guilds:
        for ch in gd.text_channels:
            await ch.send(client.appinfo.description)
            await ch.send(help_text)
    loop = asyncio.get_running_loop() # has to use their event_loop to send messages
    check_loop = threading.Thread(target = lib.checking_loop, args=[client, loop], daemon=True)
    check_loop.start()
            
    
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content == '/dm me':
        dm = await client.create_dm(message.author)
        await dm.send('suh duh')
        await dm.send('good times')

    if message.content == '/latest':
        newest_update = lib.latest("swordking")
        await message.channel.send(newest_update)

    if message.content == '/refresh':
       await message.channel.send(lib.refresh())

    if message.content == '/shutdown':
        await client.close()

    if message.content == '/help':
        await message.channel.send(help_text)

    if message.content == '/last_checked':
        await message.channel.send("Last checked at " + lib.last_scrape())

    if message.content == '/purge' and client.get_user(int(CHANNEL_OWNER)):
        await message.channel.purge(check = lambda x : True)

client.run(BOT_KEY)
