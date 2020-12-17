from typing import Sequence, Text

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from optimade_gateway import __version__

APP = FastAPI(
    title="OPTIMADE Gateway",
    description="A gateway server to query multiple OPTIMADE databases.",
    version=__version__,
)


@APP.get("/optimade")
def get_root() -> JSONResponse:
    """Introspective overview of gateway server."""
    return JSONResponse(content={"data": {}}, status_code=200)


@APP.get("/gateways")
def get_root() -> JSONResponse:
    """Introspective overview of all currently active gateways."""
    return JSONResponse(content={"data": {}}, status_code=200)


def run(argv: Sequence[Text] = None) -> None:
    """Run OPTIMADE Gateway REST API server."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(
        "optimade-gateway",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=run.__doc__,
    )

    parser.parse_args(args=argv)

    uvicorn.run("optimade_gateway.main:APP", reload=True)
