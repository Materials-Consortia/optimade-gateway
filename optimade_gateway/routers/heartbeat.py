"""/heartbeat

This file describes the router for:

    /heartbeat

"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from optimade.server.schemas import ERROR_RESPONSES


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/heartbeat",
    tags=["Heartbeat"],
    responses=ERROR_RESPONSES,
    operation_id="heartbeat",
)
async def get_heartbeat() -> PlainTextResponse:
    """`GET /heartbeat`

    Return `200 OK` with a `plain/text` response of "OPTIMADE Gateway is alive".
    """
    return PlainTextResponse(content="OPTIMADE Gateway is alive")
