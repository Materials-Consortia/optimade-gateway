"""Tests for /queries endpoints"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from ..conftest import AsyncGatewayClient, GetGateway, MockGatewayResponses


async def test_get_queries(
    client: AsyncGatewayClient,
    top_dir: Path,
) -> None:
    """Test GET /queries"""
    from optimade_gateway.models.responses import QueriesResponse

    response = await client("/queries")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = QueriesResponse(**response.json())
    assert response

    test_data = json.loads(
        (top_dir / "tests" / "static" / "test_queries.json").read_bytes()
    )

    assert response.meta.data_returned == len(test_data)
    assert response.meta.data_available == len(test_data)
    assert not response.meta.more_data_available


async def test_post_queries(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
) -> None:
    """Test POST /queries"""
    import asyncio

    from bson.objectid import ObjectId
    from optimade.server.routers.utils import BASE_URL_PREFIXES
    from pydantic import AnyUrl

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.queries import OptimadeQueryParameters, QueryState
    from optimade_gateway.models.responses import QueriesResponseSingle
    from optimade_gateway.mongo.database import MONGO_DB

    data = {
        "gateway_id": "singledb",
        "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 15},
    }

    mock_gateway_responses(await get_gateway(data["gateway_id"]))

    response = await client("/queries", method="post", json=data)

    assert response.status_code == 202, f"Request failed: {response.json()}"
    url = response.url

    response = QueriesResponseSingle(**response.json())
    assert response

    assert getattr(
        response.meta, f"_{CONFIG.provider.prefix}_created"
    ), response.meta.model_dump()

    datum = response.data
    assert datum, response

    assert (
        datum.attributes.query_parameters.model_dump()
        == OptimadeQueryParameters(**data["query_parameters"]).model_dump()
    ), (
        f"Response: {datum.attributes.query_parameters!r}\n\n"
        f"Test data: {OptimadeQueryParameters(**data['query_parameters'])!r}"
    )

    assert datum.links.model_dump() == {
        "self": AnyUrl(
            f"{'/'.join(str(url).split('/')[:-1])}{BASE_URL_PREFIXES['major']}"
            f"/queries/{datum.id}"
        )
    }
    assert datum.attributes.state == QueryState.CREATED
    assert datum.attributes.response is None

    mongo_filter = {"_id": ObjectId(datum.id)}
    assert await MONGO_DB["queries"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["queries"].find_one(mongo_filter)
    for key, value in data.items():
        assert db_datum[key] == value, f"Response: {db_datum!r}\n\nTest data: {data!r}"

    await asyncio.sleep(1)  # Ensure mock URL is queried


async def test_post_queries_bad_data(client: AsyncGatewayClient) -> None:
    """Test POST /queries with bad data"""
    from optimade.models import ErrorResponse, OptimadeError

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.routers.utils import collection_factory

    data = {
        "gateway_id": "non-existent",
        "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 15},
    }

    response = await client("/queries", method="post", json=data)

    assert (
        response.status_code == 404
    ), f"Request succeeded, where it should have failed: {response.json()}"

    response = ErrorResponse(**response.json())
    assert response

    assert len(response.errors) == 1, response.errors
    assert (
        response.errors[0].model_dump()
        == OptimadeError(
            title="Not Found",
            status="404",
            detail=(
                "Resource <id=non-existent> not found in "
                f"{await collection_factory(CONFIG.gateways_collection)}."
            ),
        ).model_dump()
    )


async def test_query_results(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
) -> None:
    """Test POST /queries and GET /queries/{id}"""
    import asyncio

    from optimade_gateway.models.queries import QueryState
    from optimade_gateway.models.responses import QueriesResponseSingle

    data = {
        "id": "test",
        "gateway_id": "slow-query",
        "query_parameters": {"filter": 'elements HAS "Cu" AND nelements>=4'},
    }

    mock_gateway_responses(await get_gateway(data["gateway_id"]))

    response = await client("/queries", method="post", json=data)
    assert response.status_code == 202, f"Request failed: {response.json()}"

    # Do not expect to have the query finish already
    # (Sleep shortly to make sure the query is created in the DB, but not long enough
    # for the external queries to have finished)
    await asyncio.sleep(0.5)
    response = await client(f"/queries/{data['id']}")
    assert response.status_code == 200, f"Request failed: {response.json()}"

    response = QueriesResponseSingle(**response.json())
    assert response.data.attributes.response.data == {}

    query = response.data
    assert query
    assert query.attributes.state in (QueryState.STARTED, QueryState.IN_PROGRESS)

    # Expect the query to have finished after sleeping 1 s more
    await asyncio.sleep(1)
    response = await client(f"/queries/{data['id']}")
    assert response.status_code == 200, f"Request failed: {response.json()}"

    response = QueriesResponseSingle(**response.json())
    assert response.data.attributes.response.data
    assert response.data.attributes.state == QueryState.FINISHED


async def test_errored_query_results(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
) -> None:
    """Test POST /queries and GET /queries/{id} with an erroneous response"""
    import asyncio

    from optimade_gateway.models.responses import QueriesResponseSingle

    data = {
        "id": "test",
        "gateway_id": "mix-child-index",  # Contains index meta-db - will error
        "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 15},
    }

    mock_gateway_responses(await get_gateway(data["gateway_id"]))

    response = await client("/queries", method="post", json=data)
    assert response.status_code == 202, f"Request failed: {response.json()}"

    query_id = QueriesResponseSingle(**response.json()).data.id

    await asyncio.sleep(1)  # Ensure the query finishes

    response = await client(f"/queries/{query_id}")
    assert response.status_code == 404, (
        "Request succeeded, where it should have failed:\n"
        f"{json.dumps(response.json(), indent=2)}"
    )

    response = QueriesResponseSingle(**response.json())
    assert response.data.attributes.response.errors


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_sort_no_effect(
    client: AsyncGatewayClient,
    get_gateway: GetGateway,
    mock_gateway_responses: MockGatewayResponses,
) -> None:
    """Test POST /queries with the `sort` query parameter

    Currently, the `sort` query parameter should not have an effect when used with this
    endpoint. This means if the `sort` parameter is used, the response should not
    change - it should be ignored.
    """
    import asyncio

    from optimade.models import Warnings

    from optimade_gateway.models.responses import QueriesResponseSingle
    from optimade_gateway.warnings import SortNotSupported

    gateway_id = "twodbs"

    query_params_asc = {
        "query_parameters": {"sort": "id"},
        "gateway_id": gateway_id,
    }
    query_params_desc = query_params_asc.copy()
    query_params_desc["query_parameters"]["sort"] = "-id"

    mock_gateway_responses(await get_gateway(gateway_id))

    with pytest.warns(SortNotSupported):
        response_asc = await client("/queries", method="post", json=query_params_asc)
    with pytest.warns(SortNotSupported):
        response_desc = await client("/queries", method="post", json=query_params_desc)

    assert response_asc.status_code == 202, f"Request failed: {response_asc.json()}"
    assert response_desc.status_code == 202, f"Request failed: {response_desc.json()}"

    response_asc = QueriesResponseSingle(**response_asc.json())
    assert response_asc
    response_desc = QueriesResponseSingle(**response_desc.json())
    assert response_desc

    await asyncio.sleep(1)  # Ensure the query finishes

    sort_warning = SortNotSupported()

    for response in (response_asc, response_desc):
        assert response.meta.warnings, response.model_dump_json()
        assert len(response.meta.warnings) == 1
        assert response.meta.warnings[0] == Warnings(
            title=sort_warning.title,
            detail=sort_warning.detail,
        )
