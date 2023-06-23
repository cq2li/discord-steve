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
SCRAPING_LOOP = None

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
help_text = """
1. '/refresh' to manually refresh the database of chapters
2. '/latest' and '/last_scraped' to request the latest chapter and last scrape time
3. '/dm me' for good times😉

"""

async def send_msg(channel, msg):
    await channel.send("@everyone")
    await channel.send("hi")
    await channel.send(msg)

@client.event
async def on_ready():
    global SCRAPING_LOOP
    logging.info(f'We have logged in as {client.user}')
    if not hasattr(client, 'appinfo'):
        client.appinfo = await client.application_info()
        # print(client.appinfo)
    for gd in client.guilds:
        for ch in gd.text_channels:
            await ch.send(client.appinfo.description)
            await ch.send(help_text)
    loop = asyncio.get_running_loop() # has to use their event_loop to send messages
    SCRAPING_LOOP = threading.Thread(target = lib.checking_loop, args=[client, loop], daemon=True)
    SCRAPING_LOOP.start()
            
    
@client.event
async def on_message(message):
    global SCRAPING_LOOP

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

    if message.content == '/last_scraped':
        await message.channel.send("Last scraped at " + lib.last_scrape())

    if message.content == '/purge' and client.get_user(int(CHANNEL_OWNER)):
        await message.channel.purge(check = lambda x : True)

    if message.content == '/check_threads':
        await message.channel.send(threading.enumerate())

    if message.content == '/check_scraper':
        if SCRAPING_LOOP:
            await message.channel.send("Running" if SCRAPING_LOOP.is_alive() else "Crashed")
        else:
            await message.channel.send("Not initialised")

    if message.content == '/set_verbose 0':
        lib.VERBOSE = 0
        await message.channel.send(f'VERBOSE set to {lib.VERBOSE}')
    if message.content == '/set_verbose 1':
        lib.VERBOSE = 1
        await message.channel.send(f'VERBOSE set to {lib.VERBOSE}')
    
    if message.content == '/start_scrape':
        if not SCRAPING_LOOP.is_alive():
            try:
                loop = asyncio.get_running_loop() # has to use their event_loop to send messages
                SCRAPING_LOOP = threading.Thread(target = lib.checking_loop, args=[client, loop], daemon=True)
                SCRAPING_LOOP.start()
                await message.channel.send("Successfully restarted")
            except Exception as e:
                await message.channel.send(str(e))
        else:
            await message.channel.send("Already running")

client.run(BOT_KEY)
