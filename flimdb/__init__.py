__version__ = "2.1.1"
import asyncio  # isort:skip

try:
    import uvloop  # isort:skip

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())  # isort:skip
except:
    pass

APP_NAME = "FLIMDb"

import os  # isort:skip

ENV = os.getenv(f"{APP_NAME.upper()}_ENV", "config")  # isort:skip

import kick  # isort:skip

kick.start(APP_NAME.lower())  # isort:skip

from kick import config, logger  # isort:skip
import json
from pathlib import Path

logger.debug("CONFIG: {%s}", json.dumps(config, indent=4))

# pylint: disable=no-member
CACHE_DIR = Path.home() / ".cache" / "flimdb"
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(parents=True)

LOG_DIR = Path.home() / ".log" / "flimdb"
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True)
