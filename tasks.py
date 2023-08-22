"""Repository management tasks powered by `invoke`.

More information on `invoke` can be found at http://www.pyinvoke.org/.
"""
# pylint: disable=import-outside-toplevel,too-many-locals
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from invoke import task

if TYPE_CHECKING:
    from typing import Optional, Tuple


TOP_DIR = Path(__file__).parent.resolve()


def update_file(
    filename: str, sub_line: "Tuple[str, str]", strip: "Optional[str]" = None
) -> None:
    """Utility function for tasks to read, update, and write files"""
    with open(filename, "r", encoding="utf8") as handle:
        lines = [
            re.sub(sub_line[0], sub_line[1], line.rstrip(strip)) for line in handle
        ]

    with open(filename, "w", encoding="utf8") as handle:
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
            "Error: Please specify version as "
            "'Major.Minor.Patch(-Pre-Release+Build Metadata)' or "
            "'vMajor.Minor.Patch(-Pre-Release+Build Metadata)'"
        )
    ver = match.group("version")

    update_file(
        TOP_DIR / "optimade_gateway/__init__.py",
        (r'__version__ = ".*"', f'__version__ = "{ver}"'),
    )
    update_file(
        TOP_DIR / "optimade_gateway/config.json",
        (r'"version": ".*",', f'"version": "{ver}",'),
    )
    update_file(
        TOP_DIR / "tests/static/test_config.json",
        (r'"version": ".*",', f'"version": "{ver}",'),
    )

    print(f"Bumped version to {ver}")
