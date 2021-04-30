import re
import sys
from typing import Tuple
from pathlib import Path

from invoke import task


TOP_DIR = Path(__file__).parent.resolve()


def update_file(filename: str, sub_line: Tuple[str, str], strip: str = None):
    """Utility function for tasks to read, update, and write files"""
    with open(filename, "r") as handle:
        lines = [
            re.sub(sub_line[0], sub_line[1], line.rstrip(strip)) for line in handle
        ]

    with open(filename, "w") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


@task(help={"ver": "OPTIMADE Gateway version to set"})
def setver(_, ver=""):
    """Sets the OPTIMADE Gateway version"""
    match = re.fullmatch(
        (
            r"v?(?P<version>[0-9]+(\.[0-9]+){2}"  # Major.Minor.Patch
            r"(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"  # pre-release
            r"(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?)"  # build metadata
        ),
        ver,
    )
    if not match:
        sys.exit(
            "Error: Please specify version as 'Major.Minor.Patch(-Pre-Release+Build Metadata)' or 'vMajor.Minor.Patch(-Pre-Release+Build Metadata)'"
        )
    ver = match.group("version")

    update_file(
        TOP_DIR.joinpath("optimade_gateway/__init__.py"),
        (r'__version__ = ".*"', f'__version__ = "{ver}"'),
    )
    update_file(
        TOP_DIR.joinpath("optimade_gateway/config.json"),
        (r'"version": ".*",', f'"version": "{ver}",'),
    )
    update_file(
        TOP_DIR.joinpath("tests/static/test_config.json"),
        (r'"version": ".*",', f'"version": "{ver}",'),
    )
    update_file(
        TOP_DIR.joinpath(".github/docker/docker_config.json"),
        (r'"version": ".*",', f'"version": "{ver}",'),
    )

    print(f"Bumped version to {ver}")
