from pathlib import Path
import re

from setuptools import setup, find_packages


TOP_DIR = Path(__file__).parent.resolve()

with open(TOP_DIR / "optimade_gateway/__init__.py", "r") as handle:
    VERSION = AUTHOR = AUTHOR_EMAIL = None
    for line in handle.readlines():
        VERSION_match = re.match(
            r'__version__ = "(?P<version>[0-9]+(\.[0-9]+){2})"', line
        )
        AUTHOR_match = re.match(r'__author__ = "(?P<author>.+)"', line)
        AUTHOR_EMAIL_match = re.match(
            r'__author_email__ = "(?P<email>.+@.+\..+)"', line
        )

        if VERSION_match is not None:
            VERSION = VERSION_match
        if AUTHOR_match is not None:
            AUTHOR = AUTHOR_match
        if AUTHOR_EMAIL_match is not None:
            AUTHOR_EMAIL = AUTHOR_EMAIL_match

    for info, value in {
        "version": VERSION,
        "author": AUTHOR,
        "author email": AUTHOR_EMAIL,
    }.items():
        if value is None:
            raise RuntimeError(
                f"Could not determine {info} from {TOP_DIR / 'optimade_gateway/__init__.py'} !"
            )
    VERSION = VERSION.group("version")
    AUTHOR = AUTHOR.group("author")
    AUTHOR_EMAIL = AUTHOR_EMAIL.group("email")

with open(TOP_DIR / "requirements.txt", "r") as handle:
    BASE = [
        f"{_.strip()}"
        for _ in handle.readlines()
        if not _.startswith("#") and "git+" not in _
    ]

with open(TOP_DIR / "requirements_dev.txt", "r") as handle:
    DEV = [
        f"{_.strip()}"
        for _ in handle.readlines()
        if not _.startswith("#") and "git+" not in _
    ]

setup(
    name="optimade-gateway",
    version=VERSION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url="https://github.com/epfl-theos/optimade-gateway",
    description="A gateway server to query multiple OPTIMADE databases.",
    long_description=(TOP_DIR / "README.md").read_text(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=BASE,
    extras_require={"dev": DEV},
    entry_points={
        "console_scripts": ["optimade-gateway = optimade_gateway.main:run"],
    },
)
