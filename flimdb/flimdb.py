#!/usr/bin/env python
import os
import subprocess
from urllib.parse import urljoin

import fire
import kick
import requests
from huey import crontab
from gevent import monkey
from setuptools import Distribution
from setuptools.command.install import install

from . import LOG_DIR, APP_NAME, huey, config, logger
from .filelist import Filelist
from .movielib import Movie, db, select, db_session

monkey.patch_all()

URL = 'http://www.imdb.com/'
WATCHLIST_URL = urljoin(URL, f'user/{config.imdb.user_id}/watchlist')
EXPORT_URL = urljoin(URL, 'list/export')
filelist = Filelist(**config.filelist.auth)


class OnlyGetScriptPath(install):
    def run(self):
        self.distribution.install_scripts = self.install_scripts


def get_setuptools_script_dir():
    " Get the directory setuptools installs scripts to for current python "
    dist = Distribution({'cmdclass': {'install': OnlyGetScriptPath}})
    dist.dry_run = True  # not sure if necessary
    dist.parse_config_files()
    command = dist.get_command_obj('install')
    command.ensure_finalized()
    command.run()
    return dist.install_scripts


@huey.task()
@db_session
def download(movie):
    if isinstance(movie, str):
        movie = Movie[movie]

    logger.info(f'Downloading {movie.title} [{movie.url}]')

    torrent = filelist.best_movie(imdb_id=movie.id)
    if torrent:
        filelist.download(torrent)
        movie.downloaded = True


@db_session
def watchlist():
    params = {
        'list_id': config.imdb.watchlist_id,
        'author_id': config.imdb.user_id
    }
    resp = requests.get(EXPORT_URL, params=params, cookies=config.imdb.cookies)
    movies = Movie.from_csv(resp.content.decode('utf-8', 'ignore'))

    return movies


@huey.periodic_task(crontab(minute=f'*/{config.polling.new_movies_minutes}'))
def check_watchlist():
    logger.debug('Checking watchlist')
    with db_session:
        for movie in watchlist():
            download(movie.id)


@huey.periodic_task(crontab(hour=f'*/{config.polling.longterm_hours}', minute='0'))
def check_longterm_watchlist():
    logger.debug('Checking longterm watchlist')
    with db_session:
        for movie in select(m for m in Movie if not m.downloaded):
            download(movie.id)


def update_config(name='config'):
    kick.update_config(APP_NAME.lower(), variant=name)


def run(debug=False, huey_consumer_path=None):
    check_watchlist()
    check_longterm_watchlist()

    db.disconnect()
    huey_consumer_path = huey_consumer_path or os.path.join(get_setuptools_script_dir(), 'huey_consumer')
    huey_cmd = [huey_consumer_path, 'flimdb.flimdb.huey', '-w', '10', '-k', 'greenlet', '--logfile', str(LOG_DIR / 'huey.log'), '-C']
    if debug:
        huey_cmd.append('--verbose')
    logger.info(f'Running consumer using: \n\t{" ".join(huey_cmd)}')

    subprocess.run(huey_cmd)


def main():
    try:
        fire.Fire()
    except KeyboardInterrupt:
        logger.info('Quitting')


if __name__ == '__main__':
    main()
