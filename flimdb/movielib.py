import os
import csv
import logging
from io import StringIO
from datetime import datetime

from pony.orm import *
from dateutil.parser import parse

from . import CACHE_DIR

if os.getenv('DEBUG'):
    sql_debug(True)
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger('pony.orm.sql').setLevel(logging.DEBUG)

db = Database()


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
    def from_csv(cls, csv_string):
        movies = []
        with StringIO(csv_string) as f:
            reader = csv.DictReader(f, dialect='unix')
            for row in reader:
                id = row.get("Const", '')
                if not Movie.exists(id=id):
                    movie = cls(
                        id=id,
                        added=parse(row.get("Created", '2018')),
                        modified=parse(row.get("Modified", '2018')),
                        description=row.get("Description", ''),
                        title=row.get("Title", ''),
                        type=row.get("Title Type", ''),
                        directors=row.get("Directors", ''),
                        rating=float(row.get("IMDb Rating", 0.0)),
                        runtime=int(row.get("Runtime (mins)", 0)),
                        year=int(row.get("Year", 2018)),
                        genres=row.get("Genres", ''),
                        votes=int(row.get("Num Votes", 0)),
                        released=parse(row.get("Release Date", '2018')),
                        url=row.get("URL", ''),
                        downloaded=False
                    )
                    movies.append(movie)

        return movies


db.bind(create_db=True, provider='sqlite', filename=str(CACHE_DIR / 'flimdb.db'))
db.generate_mapping(create_tables=True)
