import re
from enum import IntEnum
from datetime import datetime
from urllib.parse import urljoin

from dateutil import parser

from . import config

SIZE_MULTIPLIERS = {
    'K': 1_000,
    'M': 1_000_000,
    'G': 1_000_000_000,
}


class Category(IntEnum):
    TOATE = 0
    FILME_SD = 1
    FILME_DVD = 2
    FILME_DVD_RO = 3
    FILME_HD = 4
    FLAC = 5
    FILME_4K = 6
    XXX = 7
    PROGRAME = 8
    JOCURI_PC = 9
    JOCURI_CONSOLE = 10
    AUDIO = 11
    VIDEOCLIP = 12
    SPORT = 13
    DESENE = 15
    DOCS = 16
    LINUX = 17
    DIVERSE = 18
    FILME_HD_RO = 19
    FILME_BLU_RAY = 20
    SERIALE_HD = 21
    MOBILE = 22
    SERIALE_SD = 23
    ANIME = 24
    FILME_3D = 25
    FILME_4K_BLU_RAY = 26


class SearchIn(IntEnum):
    NUME_DESCRIERE = 0
    NUME = 1
    DESCRIERE = 2
    IMDB = 3


class Sort(IntEnum):
    HIBRID = 0
    RELEVANTA = 1
    DATA = 2
    MARIME = 3
    DOWNLOADS = 4
    PEERS = 5


class Torrent:
    def __init__(
            self, title: str, url: str, download_url: str,
            date_uploaded: datetime, size: float, snatched: int,
            seeders: int, leechers: int, resolution: int,
            dolby: bool, rosubbed: bool, score: int):
        self.title = title
        self.url = url
        self.download_url = download_url
        self.date_uploaded = date_uploaded
        self.size = size
        self.snatched = snatched
        self.seeders = seeders
        self.leechers = leechers
        self.resolution = resolution
        self.dolby = dolby
        self.rosubbed = rosubbed
        self.score = score
        self.active = seeders > 0
        self.similarity = 0

    def __str__(self):
        return (
            f'{self.title} ({self.score}): '
            f'{self.resolution or ""} '
            f'{self.size / SIZE_MULTIPLIERS["G"]}GB'
            f'{" RoSubbed" if self.rosubbed else ""}'
            f'{" Dolby " if self.dolby else ""}'
            f'[{self.date_uploaded}] '
            f'⭐{self.snatched} '
            f'🔺{self.seeders} '
            f'🔻{self.leechers} '
            f'{self.url} '
            f'{self.download_url}')

    def pretty_print(self):
        return f"""Title: {self.title}
        Score: {self.score}
        Resolution: {self.resolution or 'Unknown'}
        Size: {self.size / SIZE_MULTIPLIERS['G']} GB
        RoSubbed: {'Yes' if self.rosubbed else 'No'}
        Uploaded: {self.date_uploaded}
        Snatched: {self.snatched}
        Seeders: {self.seeders}
        Leechers: {self.leechers}
        Torrent URL: {self.url}
        Download URL: {self.download_url}
        """

    @classmethod
    def from_torrent_row(cls, torrentrow):
        elems = torrentrow.cssselect('.torrenttable')
        torrent = elems[1].cssselect('span>a')[0]

        title = torrent.text_content().strip('.')
        url = urljoin(config.filelist.url, torrent.get('href'))
        download_url = urljoin(config.filelist.url, elems[3].cssselect('span>a')[0].get('href'))

        date_element = elems[5].cssselect('span>nobr>font')[0]
        date_string = f'{date_element.text}T{date_element[0].tail}'
        date_uploaded = parser.parse(date_string)

        size_string = elems[6].text_content()
        multiplier = SIZE_MULTIPLIERS.get(size_string[-2], 1)
        size = float(size_string[:-2]) * multiplier

        snatched = int(re.sub(r'\D', '', elems[7].text_content()))
        seeders = int(re.sub(r'\D', '', elems[8].text_content()))
        leechers = int(re.sub(r'\D', '', elems[9].text_content()))

        resolution = re.search(r'\d+(?=p)', title)
        if resolution:
            resolution = int(resolution.group(0))
        else:
            resolution = 0

        tags = elems[1].cssselect('span>font')
        rosubbed = False
        if tags:
            rosubbed = 'rosub' in tags[0].text_content().lower()
        rosubbed = rosubbed or ('rosub' in title.lower())
        dolby = ('dts' in title.lower()) or ('dd5.1' in title.lower())

        size_gb = (size / SIZE_MULTIPLIERS['G'])
        score = int(
            (resolution - (size_gb * 100)) -
            abs(resolution - config.filelist.preferred_resolution) * 15 +
            (rosubbed * 2000) +
            (dolby * 500) +
            (seeders * 10) +
            (leechers)
        )
        return cls(
            title, url, download_url,
            date_uploaded, size,
            snatched, seeders, leechers,
            resolution, dolby, rosubbed, score
        )
