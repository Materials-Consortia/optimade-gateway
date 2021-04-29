"""Tests for /gateways/{gateway_id}/links endpoint"""
from typing import Awaitable, Callable

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from fastapi import FastAPI
import httpx
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_gateway_links(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ]
):
    """Test GET /gateways/{gateway_id}/links"""
    from optimade.models import LinksResponse

    gateway_id = "singledb"

    response = await client(f"/gateways/{gateway_id}/links")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = LinksResponse(**response.json())
    assert response

    assert response.meta.data_returned == 2
    assert response.meta.data_available == 2
    assert not response.meta.more_data_available


async def test_get_versioned_gateway_links(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ]
):
    """Test GET /gateways/{gateway_id}/{version}/links"""
    from optimade.models import LinksResponse
    from optimade.server.routers.utils import BASE_URL_PREFIXES

    gateway_id = "singledb"

    for version in BASE_URL_PREFIXES.values():
        response = await client(f"/gateways/{gateway_id}{version}/links")

        assert response.status_code == 200, f"Request failed: {response.json()}"
        response = LinksResponse(**response.json())
        assert response

        assert response.meta.data_returned == 2
        assert response.meta.data_available == 2
        assert not response.meta.more_data_available


async def test_bad_versioned_gateway_links(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ]
):
    """Test GET /gateways/{gateway_id}/{version}/links with wrong version"""
    from optimade.models import ErrorResponse, OptimadeError
    from optimade.server.exceptions import VersionNotSupported
    from optimade.server.routers.utils import BASE_URL_PREFIXES

    gateway_id = "singledb"

    wrong_versions = [
        (
            # Correct syntax - unsupport version
            "v0.1.0",
            {
                "detail": (
                    "version v0.1.0 is not supported. Supported versions: "
                    f"{[_[1:] for _ in BASE_URL_PREFIXES.values()]}"
                ),
                "title": "Version Not Supported",
                "status": "553",
            },
        ),
        (
            # Incorrect syntax - supported version
            BASE_URL_PREFIXES["patch"][len("/v") :],
            {
                "detail": f"version MUST be one of {[_[1:] for _ in BASE_URL_PREFIXES.values()]}",
                "title": "Not Found",
                "status": "404",
            },
        ),
    ]

    for version, error_data in wrong_versions:
        error_resource = OptimadeError(**error_data)

        if version == "v0.1.0":
            with pytest.raises(
                VersionNotSupported,
                match=fr"The parsed versioned base URL '/{version}.*",
            ):
                response = await client(f"/gateways/{gateway_id}/{version}/links")
            return
        else:
            response = await client(f"/gateways/{gateway_id}/{version}/links")

        assert response.status_code == int(
            error_resource.status
        ), f"Request succeeded, where it should've failed: {response.json()}"
        response = ErrorResponse(**response.json())
        assert response

        assert response.meta.data_returned == 0
        assert response.meta.data_available == 0
        assert not response.meta.more_data_available

        assert len(response.errors) == 1
        assert response.errors == [error_resource]
