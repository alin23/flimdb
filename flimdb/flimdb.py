#!/usr/bin/env python
import asyncio
from urllib.parse import urljoin

import aiohttp
import fire
import kick
from pony.orm import db_session, select

from . import APP_NAME, config, logger
from .filelist import Filelist
from .movielib import Movie

URL = "http://www.imdb.com/"
WATCHLIST_URL = urljoin(URL, f"user/{config.imdb.user_id}/watchlist")
EXPORT_URL = urljoin(URL, f"list/{config.imdb.watchlist_id}/export")
SESSION = None
filelist = None


@db_session
async def download(movie):
    if isinstance(movie, str):
        movie = Movie[movie]

    logger.info("Downloading %s [%s]", movie.title, movie.url)

    torrent = await filelist.best_movie(imdb_id=movie.id)
    if torrent:
        await filelist.download(torrent)
        movie.downloaded = True


async def watchlist(only_new=False):
    global SESSION
    if not SESSION:
        SESSION = aiohttp.ClientSession(cookies=config.imdb.cookies)

    async with SESSION.get(EXPORT_URL) as resp:
        movies = Movie.from_csv(await resp.text(), only_new=only_new)

    return movies


@db_session
async def check_watchlist_once():
    try:
        _watchlist = await watchlist(only_new=True)
        await asyncio.gather(*[download(movie.id) for movie in _watchlist])
    except Exception as e:
        logger.exception(e)


async def check_watchlist():
    while True:
        logger.debug("Checking watchlist")
        await check_watchlist_once()
        await asyncio.sleep(config.polling.new_movies_minutes * 60)


@db_session
async def check_longterm_watchlist_once():
    try:
        await asyncio.gather(
            *[
                download(movie.id)
                for movie in select(m for m in Movie if not m.downloaded)
            ]
        )
    except Exception as e:
        logger.exception(e)


async def check_longterm_watchlist():
    while True:
        logger.debug("Checking longterm watchlist")
        await check_longterm_watchlist_once()
        await asyncio.sleep(config.polling.longterm_hours * 60 * 60)


def update_config(name="config"):
    kick.update_config(APP_NAME.lower(), variant=name)


async def watch():
    global SESSION, filelist
    async with aiohttp.ClientSession(cookies=config.imdb.cookies) as session:
        SESSION = session
        async with aiohttp.ClientSession() as filelist_session:
            filelist = Filelist(session=filelist_session, **config.filelist.auth)
            asyncio.get_event_loop().create_task(check_watchlist())
            await check_longterm_watchlist()


def main():
    global SESSION
    try:
        fire.Fire()
        if SESSION and not SESSION.closed:
            asyncio.get_event_loop().run_until_complete(SESSION.close())
    except KeyboardInterrupt:
        logger.info("Quitting")


if __name__ == "__main__":
    main()
