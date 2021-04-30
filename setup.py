from pathlib import Path
import re

from setuptools import setup, find_packages


TOP_DIR = Path(__file__).parent.resolve()

with open(TOP_DIR / "optimade_gateway/__init__.py", "r") as handle:
    VERSION = AUTHOR = AUTHOR_EMAIL = None
    for line in handle.readlines():
        VERSION_match = re.match(r'__version__ = "(?P<version>.+)"', line)
        AUTHOR_match = re.match(r'__author__ = "(?P<author>.+)"', line)
        AUTHOR_EMAIL_match = re.match(r'__author_email__ = "(?P<email>.+)"', line)

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

with open(TOP_DIR / "requirements_docs.txt", "r") as handle:
    DOCS = [
        f"{_.strip()}"
        for _ in handle.readlines()
        if not _.startswith("#") and "git+" not in _
    ]

with open(TOP_DIR / "requirements_dev.txt", "r") as handle:
    DEV = [
        f"{_.strip()}"
        for _ in handle.readlines()
        if not _.startswith("#") and "git+" not in _
    ] + DOCS

setup(
    name="optimade-gateway",
    version=VERSION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url="https://github.com/Materials-Consortia/optimade-gateway",
    description="A gateway server to query multiple OPTIMADE databases.",
    long_description=(TOP_DIR / "README.md").read_text(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=BASE,
    extras_require={"dev": DEV, "docs": DOCS},
    entry_points={
        "console_scripts": ["optimade-gateway = optimade_gateway.run:run"],
    },
    keywords="optimade materials database",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "Topic :: Database :: Database Engines/Servers",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
    ],
)
