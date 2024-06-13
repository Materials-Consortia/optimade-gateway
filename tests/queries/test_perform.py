"""Test queries/perform.py"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


async def test_db_get_all_resources_recursivity(
    httpx_mock: HTTPXMock, generic_meta: dict
) -> None:
    """Test the recursivity of db_get_all_resources()"""
    import re

    from optimade.models import LinksResponse

    from optimade_gateway.queries.perform import db_get_all_resources

    db_page_one = {
        "meta": generic_meta,
        "data": [
            {
                "id": "db_page_one",
                "type": "links",
                "attributes": {
                    "base_url": "https://first-page",
                    "name": "Page one database",
                    "description": "Page one database description.",
                    "link_type": "child",
                },
            },
        ],
        "links": {"next": "https://second-page"},
    }
    db_page_one["meta"]["more_data_available"] = True

    db_page_two = {
        "meta": generic_meta,
        "data": [
            {
                "id": "db_page_two",
                "type": "links",
                "attributes": {
                    "base_url": None,
                    "name": "Page two database",
                    "description": "Page two database description.",
                    "link_type": "child",
                },
            },
        ],
    }

    httpx_mock.add_response(
        url=re.compile(rf"{db_page_one['data'][0]['attributes']['base_url']}.*"),
        json=db_page_one,
    )
    httpx_mock.add_response(
        url=re.compile(rf"{db_page_one['links']['next']}.*"),
        json=db_page_two,
    )

    resources, _ = await db_get_all_resources(
        database=db_page_one["data"][0],
        endpoint="links",
        response_model=LinksResponse,
    )

    assert len(resources) == 2
    assert resources[0] != resources[1]
    for resource in resources:
        assert resource in [db_page_one["data"][0], db_page_two["data"][0]]


async def test_db_get_all_resources_error_response(
    httpx_mock: HTTPXMock, caplog: pytest.LogCaptureFixture, generic_meta: dict
) -> None:
    """Test db_get_all_resources when an ErrorResponse is received"""
    import re

    from optimade.models import ErrorResponse

    from optimade_gateway.queries.perform import db_get_all_resources

    response = {
        "meta": generic_meta,
        "data": [
            {
                "id": "test",
                "type": "links",
                "attributes": {
                    "name": "Test",
                    "description": "Test db.",
                    "base_url": "https://mock-response",
                    "link_type": "child",
                },
            },
        ],
    }

    httpx_mock.add_response(
        url=re.compile(rf"{response['data'][0]['attributes']['base_url']}.*"),
        json=response,
    )

    resources, _ = await db_get_all_resources(
        database=response["data"][0],
        endpoint="links",
        response_model=ErrorResponse,
    )

    assert not resources
    assert (
        f"Error while querying database (id={response['data'][0]['id']!r}). Full "
        "response:" in caplog.text
    )
