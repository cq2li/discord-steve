import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
import sqlite3
from configparser import ConfigParser

BASE_DIR = Path(__file__).resolve().parent
CONFIG = ConfigParser()
CONFIG.read(BASE_DIR / 'config.ini')
DB = "Chapter_Releases.db"
p = Path('./output')

HEADERS = { 'Accept-Language': 'en',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
## ensure no spaces in NAME
NAME = "survival-story-of-a-sword-king-in-a-fantasy-world"
URL = 'https://en.leviatanscans.com/manga/survival-story-of-a-sword-king-in-a-fantasy-world/'
API = 'ajax/chapters'

turl_API = 'https://api.tinyurl.com/create'
turl_PAYLOAD = { "domain":"tinyurl.com" }
turl_HEADERS = HEADERS.copy()
turl_HEADERS['Authorization'] = f'Bearer {CONFIG.get("tinyurl", "sekrit")}'

def connect(db):
    con = sqlite3.connect(db)
    return con, con.cursor()

def swordking_refresh():
    '''
    Scrapes Leviatan scans for lastest chapters and updates the sqlite database
    '''
    con, cur = connect(DB)
    response = requests.post(url = URL + API, headers = HEADERS)
    parsed = BeautifulSoup(response.text, 'html.parser')
    ul = parsed.find('ul', class_='main')
    ul = list(filter(lambda x: x != '\n', ul.children))
    
    result = []
    display_name = NAME.replace("-", " ").title()

    # clean release info
    for listing in ul:
        chapter = listing.a.string.strip()
        link    = listing.a["href"]
        release = listing.i.string.strip()
        try:
            release = datetime.strptime(release, '%B %d, %Y')
        except:
            release = datetime.today()
        result.append((release, chapter, display_name, link))

    # store in database
    cur.execute(f'CREATE TABLE IF NOT EXISTS swordking(release, chapter, name, link, UNIQUE(chapter) ON CONFLICT REPLACE);')
    cur.executemany("INSERT INTO swordking VALUES(?, ?, ?, ?)", result)
    con.commit()
    con.close()

def notify(row):
    '''
    returns the latest chapter information to be sent as notification

    '''
    release, chapter, manga_name, link = row
    release = datetime.fromisoformat(release)
    ## set the url to be shortened
    turl_PAYLOAD["url"] = link
    turl = requests.post(turl_API, headers = turl_HEADERS, json = turl_PAYLOAD)
    tinyurl = turl.json()['data']

    manga = f'{chapter} is the latest chapter of { manga_name.replace("-", " ").title() }, '

    ago = (datetime.now() - release).days
    ago_str = "today" if ago == 0 else str(ago) + " days ago"
    released = f'released { ago_str }.\n' 

    link = f'Read it at: { tinyurl["tiny_url"] } '
    tinyurl_time = datetime.strftime(datetime.fromisoformat(tinyurl["created_at"]), "%b %d, %Y")

    created = f'(link created on { tinyurl_time }).'

    print(manga + released + link + created)
    return manga + released + link + created

def swordking_has_new_updates(tablename):
    '''
    Return a boolean for whether a chapter has new releases
    tablename - the table name under which the manga is stored
    '''
    con, cur = connect(DB)
    cur.execute(f'CREATE TABLE IF NOT EXISTS latest(name TEXT, chapter, UNIQUE(name) ON CONFLICT REPLACE);')
    last_checked = cur.execute(f'select * from latest where name = "{tablename}";').fetchall()
    if last_checked:
        last_checked = last_checked[0]
    try:
        latest = cur.execute(f'select * from {tablename} where release = (select max(release) from {tablename});').fetchall()
        assert(len(latest) == 1)
        latest = latest[0]
    except Exception as e:
        con.close()
        print(e)
        return False
    if not latest:
        con.close()
        return False
    elif last_checked and last_checked[1] == latest[1]:
        con.close()
        return False
    else:
        cur.execute('INSERT INTO latest VALUES(?, ?)', [tablename, latest[1]])
        con.commit()
        con.close()
        return True

def swordking_latest(tablename):
    '''
    Returns the latest Chapter for a manga
    tablename - the table name under which the manga is stored
    '''
    con, cur = connect(DB)
    try:
        latest = cur.execute(f'select * from {tablename} where release = (select max(release) from {tablename});').fetchall()
        print(latest)
        assert(len(latest) == 1)
        latest = latest[0]
    except Exception as e:
        print(e)
        con.close()
        return str(e)
    con.close()
    return notify(latest)
