__version__ = '0.0.1'

APP_NAME = 'FLIMDb'

import os  # isort:skip
ENV = os.getenv(f'{APP_NAME.upper()}_ENV', 'config')  # isort:skip

import kick  # isort:skip
kick.start(f'{APP_NAME.lower()}', config_variant=ENV)  # isort:skip

from kick import config, logger  # isort:skip

from pathlib import Path

from huey.contrib.sqlitedb import SqliteHuey

CACHE_DIR = Path.home() / '.cache' / 'imdb'
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(parents=True)

LOG_DIR = Path.home() / '.log' / 'imdb'
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True)

huey = SqliteHuey('flimdb', filename=str(CACHE_DIR / 'huey.db'))
