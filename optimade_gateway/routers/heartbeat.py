"""/heartbeat

This file describes the router for:

    /heartbeat

"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/heartbeat",
    response_class=PlainTextResponse,
    tags=["Heartbeat"],
    responses={404: {"description": "Not Found"}},
    operation_id="heartbeat",
)
async def get_heartbeat() -> PlainTextResponse:
    """`GET /heartbeat`

    Return `200 OK` with a `plain/text` response of "OPTIMADE Gateway is alive".
    """
    return PlainTextResponse(content="OPTIMADE Gateway is alive")
