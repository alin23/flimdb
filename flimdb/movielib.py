import csv
import logging
import os
from datetime import datetime
from io import StringIO

from dateutil.parser import parse
from pony.orm import Database, Optional, PrimaryKey, Required, sql_debug

from . import CACHE_DIR

if os.getenv("DB_DEBUG"):
    sql_debug(True)
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("pony.orm.sql").setLevel(logging.DEBUG)

db = Database()


def tryfloat(value, default=0.0):
    try:
        return float(value)
    except:
        return default


def tryint(value, default=0):
    try:
        return int(value)
    except:
        return default


class Movie(db.Entity):
    id = PrimaryKey(str)
    added = Required(datetime)
    modified = Required(datetime)
    description = Optional(str)
    title = Optional(str)
    type = Optional(str)
    directors = Optional(str)
    rating = Optional(float)
    runtime = Optional(int)
    year = Optional(int)
    genres = Optional(str)
    votes = Optional(int)
    released = Optional(datetime)
    url = Optional(str)
    downloaded = Required(bool, default=False, index=True)

    @classmethod
    def from_csv(cls, csv_string, only_new=False):
        movies = []
        with StringIO(csv_string) as f:
            reader = csv.DictReader(f, dialect="unix")
            for row in reader:
                imdb_id = row.get("Const", "")
                if imdb_id and not Movie.exists(id=imdb_id):
                    movie = cls(
                        id=imdb_id,
                        added=parse(row.get("Created", "2018")),
                        modified=parse(row.get("Modified", "2018")),
                        description=row.get("Description", ""),
                        title=row.get("Title", ""),
                        type=row.get("Title Type", ""),
                        directors=row.get("Directors", ""),
                        rating=tryfloat(row.get("IMDb Rating", 0.0)),
                        runtime=tryint(row.get("Runtime (mins)", 0)),
                        year=tryint(row.get("Year", 2018), default=2018),
                        genres=row.get("Genres", ""),
                        votes=tryint(row.get("Num Votes", 0)),
                        released=parse(row.get("Release Date", "2018")),
                        url=row.get("URL", ""),
                        downloaded=False,
                    )
                    movies.append(movie)
                elif not only_new:
                    movies.append(Movie[imdb_id])

        return movies


db.bind(create_db=True, provider="sqlite", filename=str(CACHE_DIR / "flimdb.db"))
db.generate_mapping(create_tables=True)
