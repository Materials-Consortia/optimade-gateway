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

    from invoke import Context, Result


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


@task
def update_pytest_reqs(_):
    """Update the pytest plugins to be minimum the currently listed requirement
    versions."""
    from copy import deepcopy

    config = TOP_DIR / "pyproject.toml"
    requirements = TOP_DIR / "requirements_dev.txt"

    # Retrieve dependencies specified in the config file
    with open(config, encoding="utf8") as handle:
        for line in handle.readlines():
            plugins = re.match(r'^required_plugins = "(?P<plugins>.*)".*', line)
            if plugins:
                break
        else:
            raise RuntimeError(
                "Couldn't find the required plugins for pytest in the config file at "
                f"{config} !"
            )

    plugins = {
        dependency.group("name"): dependency.group("version")
        for dependency in [
            re.match(r"^(?P<name>[a-z-]+)>=(?P<version>[0-9]+(\.[0-9]+){1,2})$", _)
            for _ in plugins.group("plugins").split(" ")  # type: ignore[union-attr]
        ]
        if dependency
    }
    original_versions = deepcopy(plugins)

    # Update the retrieved versions with those from the requirements file
    dependencies_found_counter = 0
    with open(requirements, encoding="utf8") as handle:
        for line in handle.readlines():
            for plugin in plugins:
                dependency = re.match(
                    rf"^{plugin}~=(?P<version>[0-9]+(\.[0-9]+){{1,2}}).*", line
                )
                if not dependency:
                    continue
                dependencies_found_counter += 1
                plugins[plugin] = dependency.group("version")

    # Sanity check
    if dependencies_found_counter != len(plugins):
        raise RuntimeError(
            f"Did not find all specified dependencies from the config file ({config}) in "
            f"the development requirements file ({requirements}).\nDependencies found in "
            f"the requirements file: {dependencies_found_counter}\nDependencies found in "
            f"the config file: {len(plugins)}"
        )

    # Update the config file dependency versions (if necessary)
    for plugin in original_versions:
        if original_versions[plugin] != plugins[plugin]:
            break
    else:
        print("No updates detected; the config file is up-to-date.")
        sys.exit()

    update_file(
        config,
        (
            r"^required_plugins = .*",
            'required_plugins = "'
            f'{" ".join(f"{name}>={version}" for name, version in plugins.items())}"',
        ),
    )
    print(
        f"Successfully updated pytest config plugins:\n        {plugins}\n  (was: "
        f"{original_versions})"
    )
