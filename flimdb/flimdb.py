#!/usr/bin/env python
import asyncio
from urllib.parse import urljoin

import aiohttp
import fire
from pony.orm import commit, db_session, select

from . import APP_NAME, config, logger
from .filelist import Filelist
from .movielib import Movie

URL = "https://www.imdb.com/"
WATCHLIST_URL = urljoin(URL, f"user/{config.imdb.user_id}/watchlist")
EXPORT_URL = urljoin(URL, f"list/{config.imdb.watchlist_id}/export")
SESSION = None
filelist = None
timeout = aiohttp.ClientTimeout(total=30, connect=10)


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
    global SESSION, timeout
    if not SESSION:
        SESSION = aiohttp.ClientSession(cookies=config.imdb.cookies, timeout=timeout)

    async with SESSION.get(EXPORT_URL) as resp:
        movies = Movie.from_csv(await resp.text(), only_new=only_new)

    return movies


@db_session
async def check_watchlist_once():
    try:
        commit()
        _watchlist = await watchlist(only_new=True)
        commit()
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
        commit()
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


async def check(watchlist=True, longterm=True):
    assert watchlist or longterm

    global SESSION, filelist, timeout
    async with aiohttp.ClientSession(
        cookies=config.imdb.cookies, timeout=timeout
    ) as session:
        SESSION = session

        async with get_filelist_session() as filelist_session:
            filelist = Filelist(session=filelist_session, **config.filelist.auth)

            coros = []
            if watchlist:
                coros.append(check_watchlist_once())
            if longterm:
                coros.append(check_longterm_watchlist_once())

            await asyncio.gather(*coros)


def get_filelist_session():
    return aiohttp.ClientSession(
        timeout=timeout,
        headers={"Authorization": f"Basic {config.filelist.auth.basic}"},
        raise_for_status=True,
    )


async def watch():
    global SESSION, filelist, timeout
    async with aiohttp.ClientSession(
        cookies=config.imdb.cookies, timeout=timeout
    ) as session:
        SESSION = session
        async with get_filelist_session() as filelist_session:
            filelist = Filelist(session=filelist_session, **config.filelist.auth)
            asyncio.create_task(check_watchlist())
            await check_longterm_watchlist()


def main():
    global SESSION
    try:
        fire.Fire()
        if SESSION and not SESSION.closed:
            asyncio.run(SESSION.close())
    except KeyboardInterrupt:
        logger.info("Quitting")


if __name__ == "__main__":
    main()
