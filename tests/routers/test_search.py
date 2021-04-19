"""Tests for the /search endpoint"""
from pathlib import Path

import pytest


pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("reset_db_after")]


async def test_get_search(client, mock_responses, get_gateway, caplog):
    """Test GET /search

    By using the gateway "twodbs", but adding the versioned part to the base URL,
    this should ensure a new gateway is created, specifically for use with these versioned
    base URLs, but we can reuse the mock_responses for the "twodbs" gateway.
    """
    from optimade.models import StructureResponseMany

    from optimade_gateway.common.config import CONFIG

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    query_params = {
        "filter": 'elements HAS "Cu"',
        "page_limit": 15,
        "optimade_urls": [
            _.get("attributes", {}).get("base_url") + "/v1"
            for _ in gateway.get("databases", [{}])
        ],
    }

    mock_responses(gateway)

    response = await client("/search", params=query_params)

    assert response.status_code == 200, f"Request failed: {response.json()}"

    response = StructureResponseMany(**response.json())
    assert response.data
    assert (
        getattr(response.meta, f"_{CONFIG.provider.prefix}_query", "NOT FOUND")
        == "NOT FOUND"
    )

    assert "A new gateway was created for a query" in caplog.text, caplog.text


async def test_get_search_existing_gateway(client, mock_responses, get_gateway, caplog):
    """Test GET /search for base URLs matching an existing gateway"""
    from optimade.models import StructureResponseMany

    from optimade_gateway.common.config import CONFIG

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    query_params = {
        "filter": 'elements HAS "Cu"',
        "page_limit": 15,
        "optimade_urls": [
            _.get("attributes", {}).get("base_url")
            for _ in gateway.get("databases", [{}])
        ],
    }

    mock_responses(gateway)

    response = await client("/search", params=query_params)

    assert response.status_code == 200, f"Request failed: {response.json()}"

    response = StructureResponseMany(**response.json())
    assert response.data, f"No data: {response.json(indent=2)}"
    assert (
        getattr(response.meta, f"_{CONFIG.provider.prefix}_query", "NOT FOUND")
        == "NOT FOUND"
    ), f"Special _<prefix>_query field was found in meta. Response: {response.json(indent=2)}"

    assert "A gateway was found and reused for a query" in caplog.text, caplog.text


async def test_get_search_not_finishing(client, mock_responses, get_gateway, caplog):
    """Test GET /search for unfinished query (redirect to query URL)"""
    from optimade.models import EntryResponseMany

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.queries import QueryResource, QueryState

    gateway_id = "slow-query"
    gateway: dict = await get_gateway(gateway_id)

    query_params = {
        "filter": 'elements HAS "Cu"',
        "page_limit": 15,
        "optimade_urls": [
            _.get("attributes", {}).get("base_url")
            for _ in gateway.get("databases", [{}])
        ],
        "timeout": 0,
    }

    mock_responses(gateway)

    response = await client("/search", params=query_params)
    assert response.status_code == 200, f"Request failed: {response.json()}"

    assert "A gateway was found and reused for a query" in caplog.text, caplog.text

    response = EntryResponseMany(**response.json())
    assert response.data == [], f"Data was found in response: {response.json(indent=2)}"

    assert getattr(
        response.meta, f"_{CONFIG.provider.prefix}_query", False
    ), f"Special _<prefix>_query field not found in meta. Response: {response.json(indent=2)}"
    query: QueryResource = QueryResource(
        **getattr(response.meta, f"_{CONFIG.provider.prefix}_query")
    )
    assert query, query
    assert query.attributes.state in (QueryState.STARTED, QueryState.IN_PROGRESS), query
    assert query.attributes.query_parameters.filter == query_params["filter"], query
    assert (
        query.attributes.query_parameters.page_limit == query_params["page_limit"]
    ), query
    assert (
        query.attributes.response == query.attributes.__fields__["response"].default
    ), query
    assert query.attributes.gateway_id == gateway_id, query


async def test_post_search(client, mock_responses, get_gateway, top_dir: Path, caplog):
    """Test POST /search

    By using the gateway "twodbs", but adding the versioned part to the base URL,
    this should ensure a new gateway is created, specifically for use with these versioned
    base URLs, but we can reuse the mock_responses for the "twodbs" gateway.
    """
    import asyncio
    import json

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.queries import OptimadeQueryParameters, QueryState
    from optimade_gateway.models.responses import QueriesResponseSingle
    from optimade_gateway.mongo.database import MONGO_DB

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    data = {
        "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 15},
        "optimade_urls": [
            _.get("attributes", {}).get("base_url") + "/v1"
            for _ in gateway.get("databases", [{}])
        ],
    }

    mock_responses(gateway)

    response = await client("/search", method="post", json=data)

    assert response.status_code == 202, f"Request failed: {response.json()}"

    response = QueriesResponseSingle(**response.json())
    assert response

    assert getattr(
        response.meta, f"_{CONFIG.provider.prefix}_created"
    ), response.meta.dict()

    assert "A new gateway was created for a query" in caplog.text, caplog.text

    datum = response.data
    assert datum, response

    assert (
        datum.attributes.query_parameters.dict()
        == OptimadeQueryParameters(**data["query_parameters"]).dict()
    ), f"Response: {datum.attributes.query_parameters!r}\n\nTest data: {OptimadeQueryParameters(**data['query_parameters'])!r}"

    assert datum.attributes.state == QueryState.CREATED
    assert datum.attributes.response is None

    with open(top_dir / "tests/static/test_gateways.json") as handle:
        gateways = json.load(handle)

    assert datum.attributes.gateway_id not in [_["id"] for _ in gateways]

    mongo_filter = {"id": {"$eq": datum.id}}
    assert await MONGO_DB["queries"].count_documents(mongo_filter) == 1

    await asyncio.sleep(1)  # Ensure mock URL is queried


async def test_post_search_existing_gateway(
    client, mock_responses, get_gateway, caplog
):
    """Test POST /search for base URLs matching an existing gateway"""
    import asyncio

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.queries import OptimadeQueryParameters, QueryState
    from optimade_gateway.models.responses import QueriesResponseSingle
    from optimade_gateway.mongo.database import MONGO_DB

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    data = {
        "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 15},
        "optimade_urls": [
            _.get("attributes", {}).get("base_url")
            for _ in gateway.get("databases", [{}])
        ],
    }

    mock_responses(gateway)

    response = await client("/search", method="post", json=data)

    assert response.status_code == 202, f"Request failed: {response.json()}"

    response = QueriesResponseSingle(**response.json())
    assert response

    assert getattr(
        response.meta, f"_{CONFIG.provider.prefix}_created"
    ), response.meta.dict()

    assert "A gateway was found and reused for a query" in caplog.text, caplog.text

    datum = response.data
    assert datum, response

    assert (
        datum.attributes.query_parameters.dict()
        == OptimadeQueryParameters(**data["query_parameters"]).dict()
    ), f"Response: {datum.attributes.query_parameters!r}\n\nTest data: {OptimadeQueryParameters(**data['query_parameters'])!r}"

    assert datum.attributes.state == QueryState.CREATED
    assert datum.attributes.response is None

    assert datum.attributes.gateway_id == gateway_id

    mongo_filter = {"id": {"$eq": datum.id}}
    assert await MONGO_DB["queries"].count_documents(mongo_filter) == 1

    await asyncio.sleep(1)  # Ensure mock URL is queried