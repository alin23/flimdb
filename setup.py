import pathlib
from io import open  # pylint: disable=redefined-builtin

from setuptools import find_packages, setup

CONFIGDIR = pathlib.Path.home() / ".config" / "flimdb"
CONFIGDIR.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member

with open("flimdb/__init__.py", "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.strip().split("=")[1].strip(" '\"")
            break
    else:
        version = "0.0.1"

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

REQUIRES = [
    "fuzzywuzzy",
    "fire",
    "kick",
    "aiohttp",
    "aiodns",
    "pyorderby",
    "lxml",
    "numpy",
    "python-dateutil",
    "pony",
    "python-Levenshtein",
    "cssselect"
]

setup(
    name="flimdb",
    version=version,
    description="",
    long_description=readme,
    author="Alin Panaitiu",
    author_email="alin.p32@gmail.com",
    maintainer="Alin Panaitiu",
    maintainer_email="alin.p32@gmail.com",
    url="https://github.com/alin23/flimdb",
    license="MIT/Apache-2.0",
    keywords=[""],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy"
    ],
    install_requires=REQUIRES,
    tests_require=["coverage", "pytest"],
    packages=find_packages(),
    package_data={"flimdb": ["config/*.toml"]},
    data_files=[(str(CONFIGDIR), ["flimdb/config/config.toml"])],
    entry_points={
        "console_scripts": [
            "flimdb = flimdb.flimdb:main",
            "filelist = flimdb.filelist:main"
        ]
    }
)
