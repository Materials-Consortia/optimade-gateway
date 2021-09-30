"""Repository management tasks powered by `invoke`.

More information on `invoke` can be found at http://www.pyinvoke.org/.
"""
# pylint: disable=import-outside-toplevel,too-many-locals
import re
import sys
from typing import TYPE_CHECKING
from pathlib import Path

from invoke import task

if TYPE_CHECKING:
    from typing import Tuple

    from invoke import Context, Result


TOP_DIR = Path(__file__).parent.resolve()


def update_file(filename: str, sub_line: "Tuple[str, str]", strip: str = None) -> None:
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


@task(
    help={
        "pre-clean": "Remove the 'api_reference' sub directory prior to (re)creation."
    }
)
def create_api_reference_docs(context, pre_clean=False, pre_commit=False):
    """Create the API Reference in the documentation"""
    import os
    import shutil

    def write_file(full_path: Path, content: str) -> None:
        """Write file with `content` to `full_path`"""
        if full_path.exists():
            with open(full_path, "r", encoding="utf8") as handle:
                cached_content = handle.read()
            if content == cached_content:
                del cached_content
                return
            del cached_content
        with open(full_path, "w", encoding="utf8") as handle:
            handle.write(content)

    package_dir = TOP_DIR / "optimade_gateway"
    docs_api_ref_dir = TOP_DIR / "docs/api_reference"

    unwanted_subdirs = ("__pycache__",)

    pages_template = 'title: "{name}"\n'
    md_template = "# {name}\n\n::: {py_path}\n"
    models_template = (
        md_template + f"{' ' * 4}rendering:\n{' ' * 6}show_if_no_docstring: true\n"
    )

    if docs_api_ref_dir.exists() and pre_clean:
        shutil.rmtree(docs_api_ref_dir, ignore_errors=True)
        if docs_api_ref_dir.exists():
            sys.exit(f"{docs_api_ref_dir} should have been removed!")
    docs_api_ref_dir.mkdir(exist_ok=True)

    for dirpath, dirnames, filenames in os.walk(package_dir):
        for unwanted_dir in unwanted_subdirs:
            if unwanted_dir in dirnames:
                # Avoid walking into or through unwanted directories
                dirnames.remove(unwanted_dir)

        relpath = Path(dirpath).relative_to(package_dir)

        # Create `.pages`
        docs_sub_dir = docs_api_ref_dir / relpath
        docs_sub_dir.mkdir(exist_ok=True)
        if str(relpath) == ".":
            write_file(
                full_path=docs_api_ref_dir / ".pages",
                content=pages_template.format(name="API Reference"),
            )
        else:
            write_file(
                full_path=docs_sub_dir / ".pages",
                content=pages_template.format(
                    name=str(relpath).rsplit("/", maxsplit=1)[-1]
                ),
            )

        # Create markdown files
        for filename in filenames:
            if re.match(r".*\.py$", filename) is None or filename in (
                "__init__.py",
                "run.py",
            ):
                # Not a Python file: We don't care about it!
                # Or filename is `__init__.py`: We don't want it!
                continue

            basename = filename[: -len(".py")]
            py_path = (
                f"optimade_gateway/{relpath}/{basename}".replace("/", ".")
                if str(relpath) != "."
                else f"optimade_gateway/{basename}".replace("/", ".")
            )
            md_filename = filename.replace(".py", ".md")

            # For models we want to include EVERYTHING, even if it doesn't have a
            # doc-string
            template = models_template if str(relpath) == "models" else md_template

            write_file(
                full_path=docs_sub_dir / md_filename,
                content=template.format(name=basename, py_path=py_path),
            )

    if pre_commit:
        # Check if there have been any changes.
        # List changes if yes.
        if TYPE_CHECKING:
            context: "Context" = context

        # NOTE: grep returns an exit code of 1 if it doesn't find anything
        # (which will be good in this case).
        # Concerning the weird last grep command see:
        # http://manpages.ubuntu.com/manpages/precise/en/man1/git-status.1.html
        result: "Result" = context.run(
            "git status --porcelain docs/api_reference | grep -E '^[? MARC][?MD]' "
            "|| exit 0",
            hide=True,
        )
        if result.stdout:
            sys.exit(
                "The following files have been changed/added, please stage them:"
                f"\n\n{result.stdout}"
            )


@task
def create_docs_index(_):
    """Create the documentation index page from README.md"""
    readme = TOP_DIR / "README.md"
    docs_index = TOP_DIR / "docs/index.md"

    with open(readme, encoding="utf8") as handle:
        content = handle.read()

    replacement_mapping = [
        ("docs/", ""),
        ("(LICENSE)", "(LICENSE.md)"),
    ]

    for old, new in replacement_mapping:
        content = content.replace(old, new)

    with open(docs_index, "w", encoding="utf8") as handle:
        handle.write(content)


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
                    fr"^{plugin}~=(?P<version>[0-9]+(\.[0-9]+){{1,2}}).*", line
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
