import requests
from bs4 import BeautifulSoup
from pathlib import Path
import datetime as dt
from datetime import datetime
import sqlite3
from configparser import ConfigParser
import re
import logging
import time
import discord
import random

BASE_DIR = Path(__file__).resolve().parent
CONFIG = ConfigParser()
CONFIG.read(BASE_DIR / 'config.ini')
DB = 'Chapter_Releases.db'
p = Path('./output')

HEADERS = { 'Accept-Language': 'en',
'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
## ensure no spaces in NAME
NAME = 'survival-story-of-a-sword-king-in-a-fantasy-world'
URL = 'https://en.leviatanscans.com/manga/survival-story-of-a-sword-king-in-a-fantasy-world/'
# URL = 'https://en.leviatanscans.com/manga/the-max-leveled-hero-will-return/'
API = 'ajax/chapters'

turl_API = 'https://api.tinyurl.com/create'
turl_PAYLOAD = { 'domain':'tinyurl.com' }
turl_HEADERS = HEADERS.copy()
turl_HEADERS['Authorization'] = f'Bearer {CONFIG.get("tinyurl", "secret")}'

logging.basicConfig(
        filename = 'lib.log', 
        encoding = 'utf-8', 
        level = logging.INFO,
        format = '%(asctime)s %(message)s',
        datefmt = '%m/%d/%Y %I:%M:%S %p',
        )
logging.info("Logging starting")

LAST_SCRAPE = None

def connect(db: str):
    con = sqlite3.connect(db, isolation_level= 'DEFERRED')
    return con

def refresh():
    '''
    Scrapes Leviatan scans for lastest chapters and updates the sqlite database
    '''
    con = connect(DB)
    response = requests.post(url = URL + API, headers = HEADERS)
    parsed = BeautifulSoup(response.text, 'html.parser')
    ul = parsed.find('ul', class_='main')
    ul = list(filter(lambda x: x != '\n', ul.children))
    
    result = []
    display_name = NAME.replace('-', ' ').title()
    
    re_chapter = re.compile('Chapter (\d+)')
    re_date = re.compile('(\d+) (day|hour|min|s)?')

    # clean release info
    for listing in ul:
        chapter = listing.a.string.strip()
        try:
            chapter_number = re_chapter.match(chapter).groups()[0]
        except Exception as e:
            logging.warning(f'Could not convert {chapter} to chapter number {e}')
            continue

        link    = listing.a['href']

        release = listing.i.string.strip()

        try:
            release = datetime.strptime(release, '%B %d, %Y')
        except Exception as e:
            logging.warning(e)
            re_matched = re_date.match(release)

            if re_matched == None:
                logging.error(f'{release} was not regex matched')    
                release = datetime.today()
            else:
                delta, units = re_matched.groups()
                delta = int(delta)
                match units:
                    case 'day':
                        offset = dt.timedelta(days = -delta)
                    case 'hour':
                        offset = dt.timedelta(hours = -delta)
                    case 'min':
                        offset = dt.timedelta(minutes = -delta)
                    case 's':
                        offset = dt.timedelta(seconds = -delta)
                    case _:
                        logging.error(f'{units} was not accounted for in match')
                        offset = dt.timedelta()
                release = datetime.now() + offset
                
        result.append((release, chapter_number, display_name, link))

    # store in database, lock
    with con:
        cur = con.cursor()
        cur.execute(f'CREATE TABLE IF NOT EXISTS swordking(release, chapter INTEGER, name, link, UNIQUE(chapter) ON CONFLICT REPLACE);')
        cur.executemany('INSERT INTO swordking VALUES(?, ?, ?, ?)', result)
        con.commit()
    global LAST_SCRAPE
    LAST_SCRAPE = datetime.now()
    return f'Successful scrape of SwordKing from Leviatan'

def notify(row):
    '''
    returns the latest chapter information to be sent as notification

    '''
    release, chapter, manga_name, link = row
    release = datetime.fromisoformat(release)
    ## set the url to be shortened
    turl_PAYLOAD['url'] = link
    turl = requests.post(turl_API, headers = turl_HEADERS, json = turl_PAYLOAD)
    tinyurl = turl.json()['data']

    manga = f'Chapter {chapter} is the latest chapter of { manga_name.replace("-", " ").title() }, '

    ago = (datetime.now() - release).days
    ago_str = 'today' if ago == 0 else str(ago) + ' days ago'
    released = f'released { ago_str }.\n' 

    link = f'Read it at: { tinyurl["tiny_url"] } '
    tinyurl_time = datetime.strftime(datetime.fromisoformat(tinyurl['created_at']), '%b %d, %Y')

    created = f'(link created on { tinyurl_time }).'

    # print(manga + released + link + created)
    return manga + released + link + created

def has_new_updates(tablename: str):
    '''
    Return a boolean for whether a chapter has new releases
    tablename - the table name under which the manga is stored
    '''
    con = connect(DB)
    with con:
        cur = con.cursor()
        cur.execute(f'CREATE TABLE IF NOT EXISTS latest(name TEXT, chapter INTEGER, UNIQUE(name) ON CONFLICT REPLACE);')
        last_checked = cur.execute(f'select * from latest where name = "{tablename}";').fetchall()
        if last_checked:
            last_checked = last_checked[0]
        try:
            latest = cur.execute(f'select * from {tablename} where chapter = (select max(chapter) from {tablename});').fetchall()
            assert(len(latest) == 1)
            latest = latest[0]
        except Exception as e:
            print(e)
            return False
        if not latest:
            return False
        elif last_checked and last_checked[1] == latest[1]: # this checks max chapter
            return False
        else:
            cur.execute('INSERT INTO latest VALUES(?, ?)', [tablename, latest[1]])
            con.commit()
            return True

def latest(tablename: str):
    '''
    Returns the latest Chapter for a manga
    tablename - the table name under which the manga is stored
    '''
    con = connect(DB)
    try:
        with con:
            cur = con.cursor()
            latest = cur.execute(f'select * from {tablename} where chapter = (select max(chapter) from {tablename});').fetchall()
        # print(latest)
        assert(len(latest) == 1)
        latest = latest[0]
    except Exception as e:
        print(e)
        return str(e)
    return notify(latest)

def _latest(tablename: str):
    '''
    Returns the latest Chapter for a manga
    tablename - the table name under which the manga is stored
    Internal usage for loop
    '''
    con = connect(DB)
    try:
        with con:
            cur = con.cursor()
            latest = cur.execute(f'select * from {tablename} where release = (select max(release) from {tablename});').fetchall()
        assert(len(latest) == 1)
        latest = latest[0]
    except Exception as e:
        print(e)
        return str(e)
    return latest[0]

async def send_msg(channel, msg):
    await channel.send(msg)

def checking_loop(client: discord.Client, event_loop):
    while True:
        refresh()
        if has_new_updates('swordking'):
            channel = client.get_channel(1117858953750126744)
            update = latest('swordking')
            event_loop.create_task(channel.send('@everyone\n' + update))

        last_update = datetime.strptime(_latest('swordking'), "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        elapsed = datetime.now() - last_update
        logging.info(f'last checked at {now}')
        logging.info("Days elapsed since last refresh: " +  str(elapsed.days))
        if elapsed.days > 6:
            # check once every 5 minutes
            time.sleep(60 * 3 + random.uniform(1 * 60, 4 * 60))
        else:
            #check once every 4 hours
            # time.sleep(60 * 60 * 4)
            time.sleep(60 * 60 * 4 + random.uniform(60 * 60 * 1, 60 * 60 * 2))
        

def last_scrape():
    if isinstance(LAST_SCRAPE, datetime):
        return datetime.strftime(LAST_SCRAPE, "%Y-%m-%d %I:%M:%S %p %Z")
    return "No time found"
