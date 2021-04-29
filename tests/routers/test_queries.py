"""Tests for /queries endpoints"""
# pylint: disable=import-error,no-name-in-module
import json
from pathlib import Path
from typing import Awaitable, Callable

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from fastapi import FastAPI
import httpx
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_queries(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    top_dir: Path,
):
    """Test GET /queries"""
    from optimade_gateway.models.responses import QueriesResponse

    response = await client("/queries")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = QueriesResponse(**response.json())
    assert response

    with open(top_dir / "tests/static/test_queries.json") as handle:
        test_data = json.load(handle)

    assert response.meta.data_returned == len(test_data)
    assert response.meta.data_available == len(test_data)
    assert not response.meta.more_data_available


@pytest.mark.usefixtures("reset_db_after")
async def test_post_queries(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    mock_gateway_responses: Callable[[dict], None],
    get_gateway: Callable[[str], Awaitable[dict]],
):
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
    ), response.meta.dict()

    datum = response.data
    assert datum, response

    assert (
        datum.attributes.query_parameters.dict()
        == OptimadeQueryParameters(**data["query_parameters"]).dict()
    ), f"Response: {datum.attributes.query_parameters!r}\n\nTest data: {OptimadeQueryParameters(**data['query_parameters'])!r}"

    assert datum.links.dict() == {
        "self": AnyUrl(
            url=f"{'/'.join(str(url).split('/')[:-1])}{BASE_URL_PREFIXES['major']}/queries/{datum.id}",
            scheme=url.scheme,
            host=url.host,
        )
    }
    assert datum.attributes.state == QueryState.CREATED
    assert datum.attributes.response is None

    mongo_filter = {"_id": ObjectId(datum.id)}
    assert await MONGO_DB["queries"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["queries"].find_one(mongo_filter)
    for key in data:
        assert db_datum[key] == data[key]

    await asyncio.sleep(1)  # Ensure mock URL is queried


@pytest.mark.usefixtures("reset_db_after")
async def test_post_queries_bad_data(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ]
):
    """Test POST /queries with bad data"""
    from optimade.models import ErrorResponse, OptimadeError

    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION

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
        response.errors[0].dict()
        == OptimadeError(
            title="Not Found",
            status="404",
            detail=f"Resource <id=non-existent> not found in {GATEWAYS_COLLECTION}.",
        ).dict()
    )


@pytest.mark.usefixtures("reset_db_after")
async def test_query_results(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    mock_gateway_responses: Callable[[dict], None],
    get_gateway: Callable[[str], Awaitable[dict]],
):
    """Test POST /queries and GET /queries/{id}"""
    import asyncio
    from optimade.models import EntryResponseMany
    from optimade.models import StructureResponseMany

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.queries import QueryState, QueryResource

    data = {
        "id": "test",
        "gateway_id": "slow-query",
        "query_parameters": {"filter": 'elements HAS "Cu" AND nelements>=4'},
    }

    mock_gateway_responses(await get_gateway(data["gateway_id"]))

    response = await client("/queries", method="post", json=data)
    assert response.status_code == 202, f"Request failed: {response.json()}"

    # Do not expect to have the query finish already
    # (Sleep shortly to make sure the query is created in the DB, but not long enough for the
    # external queries to have finished)
    await asyncio.sleep(0.5)
    response = await client(f"/queries/{data['id']}")
    assert response.status_code == 200, f"Request failed: {response.json()}"

    response = EntryResponseMany(**response.json())
    assert response.data == []

    query: QueryResource = QueryResource(
        **getattr(response.meta, f"_{CONFIG.provider.prefix}_query")
    )
    assert query
    assert query.attributes.state in (QueryState.STARTED, QueryState.IN_PROGRESS)

    # Expect the query to have finished after sleeping 1 s more
    await asyncio.sleep(1)
    response = await client(f"/queries/{data['id']}")
    assert response.status_code == 200, f"Request failed: {response.json()}"

    response = StructureResponseMany(**response.json())
    assert response.data
    assert (
        getattr(response.meta, f"_{CONFIG.provider.prefix}_query", "NOT FOUND")
        == "NOT FOUND"
    )


@pytest.mark.usefixtures("reset_db_after")
async def test_errored_query_results(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    mock_gateway_responses: Callable[[dict], None],
    get_gateway: Callable[[str], Awaitable[dict]],
):
    """Test POST /queries and GET /queries/{id} with an erroneous response"""
    import asyncio
    from optimade.models import ErrorResponse

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

    await asyncio.sleep(0.1)  # Ensure the query finishes

    response = await client(f"/queries/{query_id}")
    assert (
        response.status_code == 404
    ), f"Request succeeded, where it should have failed:\n{json.dumps(response.json(), indent=2)}"

    response = ErrorResponse(**response.json())
