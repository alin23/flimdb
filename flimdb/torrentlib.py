import re
from datetime import datetime
from enum import Enum, IntEnum

import addict
from dateutil import parser

from . import config

SIZE_MULTIPLIERS = {"K": 1000, "M": 1_000_000, "G": 1_000_000_000}


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


class SearchIn(Enum):
    NUME = "name"
    IMDB = "imdb"


class Sort(IntEnum):
    HIBRID = 0
    RELEVANTA = 1
    DATA = 2
    MARIME = 3
    DOWNLOADS = 4
    PEERS = 5


LOW_QUALITY_RELEASES = {
    "3GP",
    "BDSCR",
    "CAM",
    "CAMRip",
    "DVDSCR",
    "DVDSCREENER",
    "HD-CAM",
    "HD-TC",
    "HD-TS",
    "HDCAM",
    "HDTC",
    "HDTS",
    "PDVD",
    "PreDVDRip",
    "R5",
    "R5.AC3.5.1.HQ",
    "R5.LINE",
    "SCR",
    "SCREENER",
    "TC",
    "TELECINE",
    "TELESYNC",
    "TS",
}


# pylint: disable=too-many-instance-attributes


class Torrent:
    # pylint: disable=too-many-arguments

    def __init__(
        self,
        title: str,
        url: str,
        download_url: str,
        date_uploaded: datetime,
        size: float,
        snatched: int,
        seeders: int,
        leechers: int,
        resolution: int,
        dolby: bool,
        rosubbed: bool,
        score: int,
    ):
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
            f"{self.title} ({self.score}): "
            f'{self.resolution or ""} '
            f'{self.size / SIZE_MULTIPLIERS["G"]}GB'
            f'{" RoSubbed" if self.rosubbed else ""}'
            f'{" Dolby " if self.dolby else ""}'
            f"[{self.date_uploaded}] "
            f"⭐{self.snatched} "
            f"🔺{self.seeders} "
            f"🔻{self.leechers} "
            f"{self.url} "
            f"{self.download_url}"
        )

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

    @property
    def is_low_quality(self):
        return bool(set(self.title.split(".")) & LOW_QUALITY_RELEASES)

    # pylint: disable=too-many-locals

    @classmethod
    def from_torrent_row(cls, torrentrow):
        torrent = addict.Dict(torrentrow)

        title = torrent.name.lower()
        resolution = re.search(r"\d+(?=p)", title)
        if resolution:
            resolution = int(resolution.group(0))
        else:
            resolution = 0

        rosubbed = "rosub" in title
        dolby = ("dts" in title) or ("dd5.1" in title)

        size_gb = torrent.size / SIZE_MULTIPLIERS["G"]
        score = int(
            (resolution - (size_gb * 200))
            - abs(resolution - config.filelist.preferred_resolution) * 20
            + (rosubbed * 2000)
            + (dolby * 50)
            + (torrent.seeders * 10)
            + (torrent.leechers)
        )
        return cls(
            torrent.name,
            f"https://filelist.io/details.php?id={torrent.id}",
            torrent.download_link,
            parser.parse(torrent.upload_date),
            torrent.size,
            torrent.times_completed,
            torrent.seeders,
            torrent.leechers,
            resolution,
            dolby,
            rosubbed,
            score,
        )
