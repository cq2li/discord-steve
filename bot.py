import discord, lib, asyncio, logging, threading, const_texts, datetime as dt
from configparser import ConfigParser
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = ConfigParser()
CONFIG.read(BASE / 'config.ini')
BOT_KEY = CONFIG.get('discord', 'bot_secret')
CHANNEL_OWNER = CONFIG.get('discord', 'channel_owner')
SCRAPING_LOOP = None

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
THREADS = {}

def daemon_wrap(target):
    '''
    A decorator function that restarts the daemon threads upon crash
    '''
    def wrapper(*args):
        counter = 5
        counter_modified = dt.datetime.now()
        thread_name = threading.current_thread().name
        while True:
            try:
                logging.info(f'Trying to start {thread_name}\n')
                target(*args)
            except Exception as e:
                # reset the counter if it's been more than 24 hours since the last crash
                if counter < 5 and (dt.datetime.now() - counter_modified).days > 0:
                    counter = 5
                else:
                    counter -= 1
                logging.exception(f'{thread_name} raised {e}\n')
                # stop the thread if it crashed more than 5 times in the last 24 hours
                if counter == 0:
                    logging.info(f'{thread_name} closing thread')
                    break
    return wrapper

@client.event
async def on_ready():
    '''
    When the bot is running, initalise all the threads after this point to ensure
    the event loop is running

    '''
    logging.info(f'We have logged in as {client.user}')
    
    # retrieve the client application info for meta information
    if not hasattr(client, 'appinfo'):
        client.appinfo = await client.application_info()
    
    # send help message texts
    for gd in client.guilds:
        for ch in gd.text_channels:
            await ch.send(client.appinfo.description)
            await ch.send(const_texts.help_text)
    
    # initialise thread dictionary
    THREADS["leviatanDaemon"] = threading.Thread(
            target = daemon_wrap(lib.daemon_refresh),                          
            args=[client, asyncio.get_running_loop()], 
            daemon=True, 
            name="leviathanDaemon")
    THREADS["leviatanDaemon"].start()
            
    
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

    if message.content == '/last_scraped':
        await message.channel.send("Last scraped at " + lib.last_scrape())

    if message.content == '/purge' and client.get_user(int(CHANNEL_OWNER)):
        await message.channel.purge(check = lambda x : True)

    if message.content == '/check_threads':
        await message.channel.send(threading.enumerate())

    if message.content == '/check_scraper':
        if THREADS['leviatanDaemon']:
            await message.channel.send("Running" if THREADS['leviatanDaemon'].is_alive() else "Crashed")
        else:
            await message.channel.send("Not initialised")

    if message.content == '/set_verbose 0':
        lib.VERBOSE = 0
        await message.channel.send(f'VERBOSE set to {lib.VERBOSE}')
    if message.content == '/set_verbose 1':
        lib.VERBOSE = 1
        await message.channel.send(f'VERBOSE set to {lib.VERBOSE}')

client.run(BOT_KEY)
