import argparse
import os
from pathlib import Path
from typing import Sequence, Text

import uvicorn


def run(argv: Sequence[Text] = None) -> None:
    """Run OPTIMADE Gateway REST API server."""
    parser = argparse.ArgumentParser(
        "optimade-gateway",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=run.__doc__,
    )

    parser.parse_args(args=argv)

    os.environ["OPTIMADE_GATEWAY_CONFIG_FILE"] = os.environ[
        "OPTIMADE_CONFIG_FILE"
    ] = str(Path(__file__).parent.joinpath("config.json").resolve())

    uvicorn.run(
        "optimade_gateway.main:APP",
        reload=True,
        reload_dirs=[str(Path(__file__).parent.resolve())],
    )
