import discord, lib, asyncio, logging, threading, const_texts, datetime as dt
from configparser import ConfigParser
from pathlib import Path
from discord import app_commands

BASE = Path(__file__).resolve().parent
CONFIG = ConfigParser()
CONFIG.read(BASE / 'config.ini')
BOT_KEY = CONFIG.get('discord', 'bot_secret')
CHANNEL_OWNER = CONFIG.get('discord', 'channel_owner')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
THREADS = {}


def daemon_restart(target):
    '''
    A decorator function that restarts the daemon threads upon crash with a limit amount
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
                    send_message(f'{thread_name} exiting, too many restarts', *args)
                    break
    return wrapper


def send_message(msg, client, event_loop):
    '''
    Enable discord message sending
    '''
    channel = client.get_channel(int(CONFIG.get('discord', 'general_channel')))
    event_loop.create_task(channel.send(msg))




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
    
    # initialise thread dictionary
    THREADS["leviatan_daemon"] = threading.Thread(
            target = daemon_restart(lib.daemon_refresh),                          
            args=[client, asyncio.get_running_loop()], 
            daemon=True, 
            name="leviathan_daemon")
    THREADS["leviatan_daemon"].start()
    await tree.sync(guild=discord.Object(id=int(CONFIG.get('discord', 'server_id'))))


@client.event
async def on_message(message):

    if message.author == client.user:
        return
    
    if message.content == '/dm me':
        dm = await client.create_dm(message.author)
        await dm.send('good times')

    if message.content == '/shutdown':
        await client.close()


def tree_guild(func):
    '''
    Convenience decorator for including guild id in slash commands
    '''
    cmd = tree.command(guild = discord.Object(id=int(CONFIG.get('discord', 'server_id'))))(func)
    async def decorate(*args):
        # cmd = tree.command(guild = discord.Object(id=int(CONFIG.get('discord', 'server_id'))))(func)
        await cmd(*args)
    return decorate


@tree_guild
async def check_threads(ctx):
    '''
    Checks the status of running daemons
    '''
    for thread in THREADS:
        await ctx.response.send_message(f'{thread} is running')


@tree_guild
async def toggle_verbose(ctx):
    '''
    Toggles message verbosity
    '''
    lib.VERBOSE = not lib.VERBOSE
    await ctx.response.send_message(f'VERBOSE set to {lib.VERBOSE}')


@tree_guild
async def purge(ctx):
    '''
    Clears all channel history
    '''
    if ctx.user.id == int(CHANNEL_OWNER):
        await ctx.response.defer(ephemeral = True)
        await ctx.channel.purge(check = lambda x : True)
        await ctx.followup.send("History Cleared")


@tree_guild
async def check_last_update_time(ctx):
    '''
    Displays last updated time
    '''
    await ctx.response.send_message("Last updated at " + lib.last_scrape())


@tree_guild
async def help_me(ctx):
    '''
    Sends useless info
    '''
    await ctx.response.send_message(const_texts.help_text)


@tree_guild
async def latest_chapters(ctx):
    '''
    Sends newest chapters
    '''
    newest_update = lib.latest("swordking")
    await ctx.response.send_message(newest_update)

 
@tree_guild
async def update_database(ctx):
    '''
    Refreshes database manually
    '''
    await ctx.response.send_message(lib.refresh())


@tree_guild
async def restart(ctx):
    '''
    Forces a bot restart
    '''
    if ctx.user.id == (int(CHANNEL_OWNER)):
        await ctx.response.send_message('restarting')
        await client.close()


@tree_guild
async def goodtimes(ctx):
    '''
    FOR GOOD TIMES
    '''
    dm = await client.create_dm(ctx.user)
    await ctx.response.send_message('😎')
    await dm.send('good times')
    


client.run(BOT_KEY)
