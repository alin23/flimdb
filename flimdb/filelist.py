#!/usr/bin/env python

import asyncio
import pathlib
from operator import attrgetter
from urllib.parse import urljoin

import aiohttp
import fire
import numpy as np
from fuzzywuzzy import fuzz
from lxml.html import fromstring
from pyorderby import desc

from . import config, logger
from .torrentlib import Category, SearchIn, Sort, Torrent


class Filelist:
    """Filelist helper"""

    URL = "https://filelist.ro"
    AUTH_URL = urljoin(URL, "takelogin.php")
    LOGIN_URL = urljoin(URL, "login.php")
    SEARCH_URL = urljoin(URL, "browse.php")

    MOVIE_CATEGORIES = [
        Category.FILME_4K,
        Category.FILME_HD_RO,
        Category.FILME_HD,
        Category.FILME_BLU_RAY,
        Category.FILME_DVD_RO,
        Category.FILME_SD,
        Category.FILME_DVD
    ]

    def __init__(self, username=None, password=None, torrentdir=None, session=None):
        super(Filelist, self).__init__()
        self.username = username
        self.password = password
        self.torrentdir = pathlib.Path(torrentdir)
        self.session = session

    async def _request(self, method, url, *args, **kwargs):
        if not self.session:
            self.session = aiohttp.ClientSession()
        resp = await self.session.request(method, url, *args, **kwargs)
        if not resp.url.human_repr().startswith(self.LOGIN_URL):
            return resp

        await self.authenticate()
        return await self.session.request(method, url, *args, **kwargs)

    @staticmethod
    def _normalize_scores(scores, _max=100, _min=0):
        return np.digitize(
            _max + _max * (scores - np.max(scores)) / (np.ptp(scores) - _min),
            np.arange(_min, _max)
        )

    async def get(self, url, *args, **kwargs):
        return await self._request("GET", url, *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self._request("POST", url, *args, **kwargs)

    async def authenticate(self):
        data = {"username": self.username, "password": self.password}
        return await self.session.post(self.AUTH_URL, data=data)

    async def search(
        self,
        query,
        cat=Category.TOATE,
        searchin=SearchIn.NUME_DESCRIERE,
        sort=Sort.HIBRID,
        fields=None
    ):
        params = {
            "search": query,
            "cat": Category(cat).value,
            "searchin": SearchIn(searchin).value,
            "sort": Sort(sort).value
        }
        r = await self.get(self.SEARCH_URL, params=params)
        async with r:
            dom = fromstring(await r.text())
        torrents = dom.cssselect(".torrentrow")
        torrents = map(Torrent.from_torrent_row, torrents)
        torrents = list(filter(lambda t: t.active and not t.is_low_quality, torrents))

        if fields:
            return list(map(attrgetter(*fields), torrents))

        return torrents

    async def download(self, torrent: Torrent):
        url = torrent.download_url
        torrent_file = self.torrentdir / f"{torrent.title}.torrent"

        r = await self.get(url)
        async with r:
            if r.status == 200:
                torrent_file.write_bytes(await r.read())

        return torrent_file

    async def movie_torrents(self, imdb_id=None, title=None):
        if imdb_id:
            searchin = SearchIn.IMDB
        elif title:
            searchin = SearchIn.NUME
        else:
            raise Exception("No arguments provided")

        torrents = []
        for cat in self.MOVIE_CATEGORIES:
            torrents = await self.search(imdb_id or title, cat=cat, searchin=searchin)
            if torrents:
                break

        if not torrents:
            return []

        scores = self._normalize_scores([t.score for t in torrents])
        for torrent, score in zip(torrents, scores):
            torrent.score = score
            torrent.similarity = fuzz.partial_ratio(title, torrent.title)

        order = (
            desc("$similarity > 70")
            .desc("score")
            .desc("rosubbed")
            .desc("active")
            .desc("resolution")
            .desc("date_uploaded")
        )
        torrents = list(sorted(torrents, key=order))
        return torrents

    async def best_movie(self, title=None, imdb_id=None, download=False):
        torrents = []
        if imdb_id:
            torrents = await self.movie_torrents(imdb_id=imdb_id)
        if not torrents and title:
            torrents = await self.movie_torrents(title=title)
        if not torrents:
            logger.error("No movie found for title={%s}, imdb_id={%s}", title, imdb_id)
            return None

        torrent = torrents[0]
        logger.info(torrent.pretty_print())

        if download:
            await self.download(torrent)

        return torrent


def main():
    filelist = Filelist(**config.filelist.auth)
    fire.Fire(filelist)
    asyncio.run(filelist.session.close())


if __name__ == "__main__":
    main()
