#!/usr/bin/env python

import pathlib
from operator import attrgetter
from urllib.parse import urljoin

import numpy as np
import requests
from lxml.html import fromstring
from pyorderby import asc, desc

import fire
from fuzzywuzzy import fuzz

from . import config, logger
from .torrentlib import Sort, Torrent, Category, SearchIn


class Filelist(object):
    """Filelist helper"""

    URL = 'http://filelist.ro'
    AUTH_URL = urljoin(URL, 'takelogin.php')
    LOGIN_URL = urljoin(URL, 'login.php')
    SEARCH_URL = urljoin(URL, 'browse.php')

    MOVIE_CATEGORIES = [
        Category.FILME_4K,
        Category.FILME_HD_RO,
        Category.FILME_HD,
        Category.FILME_BLU_RAY,
        Category.FILME_DVD_RO,
        Category.FILME_SD,
        Category.FILME_DVD,
    ]

    def __init__(self, username, password, torrentdir):
        super(Filelist, self).__init__()
        self.username = username
        self.password = password
        self.torrentdir = pathlib.Path(torrentdir)
        self.session = requests.session()

    def _request(self, method, url, *args, **kwargs):
        r = self.session.request(method, url, *args, **kwargs)
        if r.url == self.LOGIN_URL:
            self.authenticate()
            r = self.session.request(method, url, *args, **kwargs)

        return r

    def _normalize_scores(self, scores, _max=100, _min=0):
        return np.digitize(_max + _max * (scores - np.max(scores)) / (np.ptp(scores) - _min), np.arange(_min, _max))

    def get(self, url, *args, **kwargs):
        return self._request('GET', url, *args, **kwargs)

    def post(self, url, *args, **kwargs):
        return self._request('POST', url, *args, **kwargs)

    def authenticate(self):
        data = {'username': self.username, 'password': self.password}
        return self.session.post(self.AUTH_URL, data=data)

    def search(self, query, cat=Category.TOATE, searchin=SearchIn.NUME_DESCRIERE, sort=Sort.HIBRID, fields=None):
        params = {'search': query, 'cat': cat, 'searchin': searchin, 'sort': sort}
        r = self.get(self.SEARCH_URL, params=params)
        dom = fromstring(r.content)
        torrents = dom.cssselect('.torrentrow')
        torrents = map(Torrent.from_torrent_row, torrents)
        torrents = list(filter(lambda t: t.active and not t.is_low_quality, torrents))

        if fields:
            return list(map(attrgetter(*fields), torrents))
        return torrents

    def download(self, torrent: Torrent):
        url = torrent.download_url
        torrent_file = self.torrentdir / f'{torrent.title}.torrent'

        r = self.get(url)
        if r.status_code == 200:
            torrent_file.write_bytes(r.content)

        return torrent_file

    def movie_torrents(self, imdb_id=None, title=None):
        if imdb_id:
            searchin = SearchIn.IMDB
        elif title:
            searchin = SearchIn.NUME
        else:
            raise Exception('No arguments provided')

        torrents = []
        for cat in self.MOVIE_CATEGORIES:
            torrents = self.search(imdb_id or title, cat=cat, searchin=searchin)
            if torrents:
                break

        if not torrents:
            return []

        scores = self._normalize_scores([t.score for t in torrents])
        for torrent, score in zip(torrents, scores):
            torrent.score = score
            torrent.similarity = fuzz.partial_ratio(title, torrent.title)

        order = (
            desc('$similarity > 70').desc('score').desc('rosubbed').desc('dolby').desc('active').desc('resolution')
            .desc('date_uploaded')
        )
        torrents = list(sorted(torrents, key=order))
        return torrents

    def best_movie(self, title=None, imdb_id=None, download=False):
        torrents = []
        if imdb_id:
            torrents = self.movie_torrents(imdb_id=imdb_id)
        if not torrents and title:
            torrents = self.movie_torrents(title=title)
        if not torrents:
            logger.error(f'No movie found for title={title}, imdb_id={imdb_id}')
            return

        torrent = torrents[0]
        logger.info(torrent.pretty_print())

        if download:
            self.download(torrent)

        return torrent


def main():
    fire.Fire(Filelist(**config.filelist.auth))


if __name__ == '__main__':
    main()
