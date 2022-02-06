"""Tests for /links endpoint"""
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


async def test_get_links(
    client: (
        'Callable[ [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]], Awaitable[Response]]'
    ),
):
    """Test GET /links"""
    from optimade.models import LinksResponse

    response = await client("/links")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = LinksResponse(**response.json())
    assert response

    assert response.meta.data_returned == 2
    assert response.meta.data_available == 2
    assert not response.meta.more_data_available
