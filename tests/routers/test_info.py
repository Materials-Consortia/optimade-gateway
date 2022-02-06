"""Tests for /info endpoint"""
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import Awaitable, Callable

    try:
        from typing import Literal
    except ImportError:
        from typing_extensions import Literal

    from fastapi import FastAPI
    from httpx import Response


async def test_get_info(
    client: (
        'Callable[[str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]], Awaitable[Response]]'
    ),
):
    """Test GET /info"""
    from optimade.models import InfoResponse

    available_endpoints = sorted(
        [
            "docs",
            "gateways",
            "info",
            "links",
            "openapi.json",
            "redoc",
            "search",
            "queries",
            "databases",
        ]
    )
    entry_types_by_format = {"json": ["databases", "gateways", "queries"]}

    response = await client("/info")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = InfoResponse(**response.json())
    assert response

    assert response.meta.data_returned == 1
    assert response.meta.data_available == 1
    assert not response.meta.more_data_available
    assert response.data.attributes.available_endpoints == available_endpoints
    assert response.data.attributes.entry_types_by_format == entry_types_by_format
    assert (
        not response.data.attributes.is_index
        or response.data.attributes.is_index is None
    )


async def test_get_info_entry(
    client: (
        'Callable[[str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]], Awaitable[Response]]'
    ),
):
    """Test GET /info/{entry}"""
    from optimade.models import EntryInfoResponse

    from optimade_gateway.routers.info import ENTRY_INFO_SCHEMAS

    for entry_endpoint in ENTRY_INFO_SCHEMAS:
        response = await client(f"/info/{entry_endpoint}")

        assert response.status_code == 200, f"Request failed: {response.json()}"
        response = EntryInfoResponse(**response.json())
        assert response

        assert response.meta.data_returned == 1
        assert response.meta.data_available == 1
        assert not response.meta.more_data_available
