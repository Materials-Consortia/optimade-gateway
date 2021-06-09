"""Tests for /gateways/{gateway_id}/structures endpoints"""
# pylint: disable=import-error,no-name-in-module
import json
from typing import Awaitable, Callable

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from fastapi import FastAPI
import httpx
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_structures(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    get_gateway: Callable[[str], Awaitable[dict]],
    mock_gateway_responses: Callable[[dict], None],
):
    """Test GET /gateways/{gateway_id}/structures"""
    from optimade.models import StructureResponseMany

    from optimade_gateway.common.config import CONFIG

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    mock_gateway_responses(gateway)

    response = await client(f"/gateways/{gateway_id}/structures")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = StructureResponseMany(**response.json())
    assert response

    assert response.meta.more_data_available

    more_data_available = False
    data_returned = 0
    data_available = 0
    data = []

    assert len(response.data) == CONFIG.page_limit * len(gateway["databases"])

    for database in gateway["databases"]:
        url = f"{database['attributes']['base_url']}/structures?page_limit={CONFIG.page_limit}"
        db_response = httpx.get(url)
        assert (
            db_response.status_code == 200
        ), f"Request to {url} failed: {db_response.json()}"
        db_response = db_response.json()

        data_returned += db_response["meta"]["data_returned"]
        data_available += db_response["meta"]["data_available"]
        if not more_data_available:
            more_data_available = db_response["meta"]["more_data_available"]

        for datum in db_response["data"]:
            database_id_meta = {
                "_optimade_gateway_": {"source_database_id": database["id"]}
            }
            if "meta" in datum:
                datum["meta"].update(database_id_meta)
            else:
                datum["meta"] = database_id_meta
            data.append(datum)

    assert data_returned == response.meta.data_returned
    assert data_available == response.meta.data_available
    assert more_data_available == response.meta.more_data_available

    assert data == json.loads(response.json(exclude_unset=True))["data"], (
        f"IDs in test not in response: {set([_['id'] for _ in data]) - set([_['id'] for _ in json.loads(response.json(exclude_unset=True))['data']])}\n\n"
        f"IDs in response not in test: {set([_['id'] for _ in json.loads(response.json(exclude_unset=True))['data']]) - set([_['id'] for _ in data])}\n\n"
    )


async def test_get_single_structure(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    get_gateway: Callable[[str], Awaitable[dict]],
    mock_gateway_responses: Callable[[dict], None],
):
    """TEST GET /gateways/{gateway_id}/structures/{structure_id}"""
    from optimade.models import StructureResponseOne

    gateway_id = "single-structure_optimade-sample"
    structure_id = "optimade-sample_single/1"
    gateway = await get_gateway(gateway_id)

    mock_gateway_responses(gateway)

    response = await client(f"/gateways/{gateway_id}/structures/{structure_id}")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = StructureResponseOne(**response.json())
    assert response

    assert not response.meta.more_data_available

    database = [_ for _ in gateway["databases"] if "_single" in _["id"]][0]

    assert response.data is not None, f"Response:\n{response.json(indent=2)}"

    url = f"{database['attributes']['base_url']}/structures/{structure_id[len(database['id']) + 1:]}"
    db_response = httpx.get(url)
    assert (
        db_response.status_code == 200
    ), f"Request to {url} failed: {db_response.json()}"
    db_response = db_response.json()

    assert db_response["data"] is not None
    assert db_response["data"] == json.loads(response.json(exclude_unset=True))["data"]

    assert db_response["meta"]["data_returned"] == response.meta.data_returned
    assert response.meta.data_available is None
    assert (
        db_response["meta"]["more_data_available"] == response.meta.more_data_available
    )


async def test_sort_no_effect(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    get_gateway: Callable[[str], Awaitable[dict]],
    mock_gateway_responses: Callable[[dict], None],
):
    """Test GET /gateways/{gateway_id}/structures with the `sort` query parameter

    Currently, the `sort` query parameter should not have an effect when used with this endpoint.
    This means if the `sort` parameter is used, the response should not change - it should be
    ignored.
    """
    from optimade.models import StructureResponseMany, Warnings

    from optimade_gateway.warnings import SortNotSupported

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    mock_gateway_responses(gateway)

    with pytest.warns(SortNotSupported):
        response_asc = await client(f"/gateways/{gateway_id}/structures?sort=id")
    with pytest.warns(SortNotSupported):
        response_desc = await client(f"/gateways/{gateway_id}/structures?sort=-id")

    assert response_asc.status_code == 200, f"Request failed: {response_asc.json()}"
    assert response_desc.status_code == 200, f"Request failed: {response_desc.json()}"

    response_asc = StructureResponseMany(**response_asc.json())
    assert response_asc
    response_desc = StructureResponseMany(**response_desc.json())
    assert response_desc

    assert response_asc.data == response_desc.data

    sort_warning = SortNotSupported()

    for response in (response_asc, response_desc):
        assert response.meta.warnings, response.json()
        assert len(response.meta.warnings) == 1
        assert response.meta.warnings[0] == Warnings(
            title=sort_warning.title,
            detail=sort_warning.detail,
        )
