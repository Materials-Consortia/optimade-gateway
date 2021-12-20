"""Specific OPTIMADE Gateway Python exceptions."""
from optimade.models import ErrorResponse
from optimade.server.exceptions import HTTPException
from optimade.server.schemas import ERROR_RESPONSES


__all__ = ("OptimadeGatewayError",)


class OptimadeGatewayError(Exception):
    """General OPTIMADE Gateway exception."""


class Unauthorized(HTTPException):
    """401 Unauthorized"""

    status_code: int = 401
    title: str = "Unauthorized"


POSSIBLE_ERRORS = (Unauthorized,)
ERROR_RESPONSES.update(
    {
        err.status_code: {"model": ErrorResponse, "description": err.title}
        for err in POSSIBLE_ERRORS
    }
)
