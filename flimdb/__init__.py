__version__ = "2.0.2"
import asyncio  # isort:skip
import uvloop  # isort:skip

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # isort:skip

APP_NAME = "FLIMDb"

import os  # isort:skip

ENV = os.getenv(f"{APP_NAME.upper()}_ENV", "config")  # isort:skip

import kick  # isort:skip

kick.start(f"{APP_NAME.lower()}", config_variant=ENV)  # isort:skip

from kick import config, logger  # isort:skip
import json
from pathlib import Path

logger.debug("CONFIG: {%s}", json.dumps(config, indent=4))

# pylint: disable=no-member
CACHE_DIR = Path.home() / ".cache" / "imdb"
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(parents=True)

LOG_DIR = Path.home() / ".log" / "imdb"
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True)
