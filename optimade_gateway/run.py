"""Simplified function for running the server used in the CLI."""
import argparse
import os
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn

if TYPE_CHECKING or bool(os.getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    # pylint: disable=unused-import
    from typing import Optional, Sequence, Text


def run(argv: "Optional[Sequence[Text]]" = None) -> None:
    """Run OPTIMADE Gateway REST API server."""
    parser = argparse.ArgumentParser(
        "optimade-gateway",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=run.__doc__,
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Run as if in production environment.",
    )
    parser.add_argument(
        "--load-providers",
        action="store_true",
        help="Load providers from providers.optimade.org upon startup.",
    )
    parser.add_argument(
        "--atlas",
        action="store_true",
        help="Use the MongoDB Atlas 'test' server instead of localhost.",
    )

    args = parser.parse_args(args=argv)

    uvicorn_kwargs = {
        "reload": True,
        "reload_dirs": [str(Path(__file__).parent.resolve())],
        "log_level": "debug",
    }

    os.environ["optimade_load_optimade_providers_databases"] = (
        "True" if args.load_providers else "False"
    )

    if args.prod:
        print(
            "Consider running the gateway using Docker or the `uvicorn` CLI directly "
            "instead!"
        )
        uvicorn_kwargs.update({"reload": False, "log_level": "info"})
    else:
        # Use test DB
        os.environ["OPTIMADE_MONGO_DATABASE"] = "optimade_gateway_dev"
        os.environ["OPTIMADE_DEBUG"] = "True"
        os.environ["OPTIMADE_LOG_LEVEL"] = "debug"

    config_file = "config_atlas.yml" if args.atlas else "config.yml"
    os.environ["OPTIMADE_CONFIG_FILE"] = str(
        Path(__file__).resolve().parent / config_file
    )

    uvicorn.run("optimade_gateway.main:APP", **uvicorn_kwargs)
