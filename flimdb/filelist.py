#!/usr/bin/env python

import asyncio
import pathlib
from operator import attrgetter

import aiohttp
import fire
import numpy as np
from fuzzywuzzy import fuzz
from pyorderby import desc

from . import config, logger
from .torrentlib import Category, SearchIn, Torrent


class Filelist:
    """Filelist helper"""

    URL = "https://filelist.io/api.php"

    MOVIE_CATEGORIES = [
        Category.FILME_4K,
        Category.FILME_HD_RO,
        Category.FILME_HD,
        Category.FILME_BLU_RAY,
        Category.FILME_DVD_RO,
        Category.FILME_SD,
        Category.FILME_DVD,
    ]

    def __init__(self, basic=None, torrentdir=None, session=None):
        super(Filelist, self).__init__()
        self.basic_auth = basic
        self.torrentdir = pathlib.Path(torrentdir)
        self.session = session

    async def _request(self, method, url, *args, json=True, **kwargs):
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Basic {self.basic_auth}"},
                raise_for_status=True,
            )
        try:
            async with self.session.request(method, url, *args, **kwargs) as resp:
                if json:
                    return await resp.json()
                return await resp.read()
        except aiohttp.client_exceptions.ClientResponseError:
            # logger.exception(exc)
            return None

    @staticmethod
    def _normalize_scores(scores, _max=100, _min=0):
        return np.digitize(
            _max + _max * (scores - np.max(scores)) / ((np.ptp(scores) - _min) or 1),
            np.arange(_min, _max),
        )

    async def get(self, url, *args, **kwargs):
        return await self._request("GET", url, *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self._request("POST", url, *args, **kwargs)

    async def search(self, query, cat=None, searchin=SearchIn.NUME, fields=None):
        params = {
            "action": "search-torrents",
            "type": SearchIn(searchin).value,
            "query": query,
        }
        if cat:
            params["category"] = ",".join(str(Category(c).value) for c in cat)

        json_resp = await self.get(self.URL, params=params)
        if not json_resp:
            return []

        torrents = map(Torrent.from_torrent_row, json_resp)
        torrents = list(filter(lambda t: t.active and not t.is_low_quality, torrents))

        if fields:
            return list(map(attrgetter(*fields), torrents))

        return torrents

    async def download(self, torrent: Torrent):
        url = torrent.download_url
        torrent_file = self.torrentdir / f"{torrent.title}.torrent"

        torrent_bytes = await self.get(url, json=False)
        if torrent_bytes:
            torrent_file.write_bytes(torrent_bytes)

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
            torrents = await self.search(imdb_id or title, cat=[cat], searchin=searchin)
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
