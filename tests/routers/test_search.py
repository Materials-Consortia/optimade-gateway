"""Tests for the /search endpoint"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from ..conftest import AsyncGatewayClient, GetGateway, MockGatewayResponses


async def test_get_search(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test GET /search

    By using the gateway "twodbs", but adding the versioned part to the base URL,
    this should ensure a new gateway is created, specifically for use with these
    versioned base URLs, but we can reuse the mock_gateway_responses for the "twodbs"
    gateway.
    """
    from optimade_gateway.models import QueriesResponseSingle

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    query_params = {
        "filter": 'elements HAS "Cu"',
        "page_limit": 15,
        "optimade_urls": [
            f'{_.get("attributes", {}).get("base_url").rstrip("/")}/v1'
            for _ in gateway.get("databases", [{}])
        ],
    }

    mock_gateway_responses(gateway)

    response = await client("/search", params=query_params)

    assert response.status_code == 200, f"Request failed: {response.json()}"

    response = QueriesResponseSingle(**response.json())
    assert response.data.attributes.response.data
    assert response.data.attributes.state.value == "finished"

    assert "A new gateway was created for a query" in caplog.text, caplog.text
    assert "A gateway was found and reused for a query" not in caplog.text, caplog.text


async def test_get_search_existing_gateway(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test GET /search for base URLs matching an existing gateway"""
    from optimade_gateway.models import QueriesResponseSingle

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    query_params = [
        # optimade_urls
        {
            "filter": 'elements HAS "Cu"',
            "page_limit": 15,
            "optimade_urls": [
                _.get("attributes", {}).get("base_url")
                for _ in gateway.get("databases", [{}])
            ],
        },
        # database_ids
        {
            "filter": 'elements HAS "Cu"',
            "page_limit": 15,
            "database_ids": [_.get("id") for _ in gateway.get("databases", [{}])],
        },
        # Both optimade_urls & database_ids
        {
            "filter": 'elements HAS "Cu"',
            "page_limit": 15,
            "optimade_urls": [
                gateway.get("databases", [{}])[0].get("attributes", {}).get("base_url")
            ],
            "database_ids": [gateway.get("databases", [{}])[-1].get("id")],
        },
    ]

    mock_gateway_responses(gateway)

    for query_param in query_params:
        response = await client("/search", params=query_param)

        assert response.status_code == 200, f"Request failed: {response.json()}"

        response = QueriesResponseSingle(**response.json())
        assert (
            response.data.attributes.response.data
        ), f"No data: {response.model_dump_json(indent=2)}"
        assert (
            response.data.attributes.state.value == "finished"
        ), f"Query never finished. Response: {response.model_dump_json(indent=2)}"

        assert "A gateway was found and reused for a query" in caplog.text, caplog.text
        assert "A new gateway was created for a query" not in caplog.text, caplog.text


async def test_get_as_optimade(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test GET /search with `as_optimade=True`

    This should be equivalent to `GET /gateways/{gateway_id}/structures`.
    """
    import json

    from httpx import get as httpx_get
    from optimade.models import StructureResponseMany

    from optimade_gateway.common.config import CONFIG

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    query_params = {
        "filter": 'elements HAS "Cu"',
        "page_limit": CONFIG.page_limit,
        "database_ids": [_.get("id") for _ in gateway.get("databases", [{}])],
        "as_optimade": True,
    }

    mock_gateway_responses(gateway)

    response = await client("/search", params=query_params)

    assert (
        response.status_code == 200
    ), f"Request failed:\n{json.dumps(response.json(), indent=2)}"

    response = StructureResponseMany(**response.json())
    assert response

    assert response.meta.more_data_available

    more_data_available = False
    data_returned = 0
    data_available = 0
    data = []

    assert len(response.data) == query_params["page_limit"] * len(gateway["databases"])

    for database in gateway["databases"]:
        url = (
            f"{database['attributes']['base_url'].rstrip('/')}/structures"
            f"?page_limit={query_params['page_limit']}"
        )

        db_response = httpx_get(url)
        assert (
            db_response.status_code == 200
        ), f"Request to {url} failed: {db_response.json()}"
        db_response = StructureResponseMany(**db_response.json())

        data_returned += db_response.meta.data_returned
        data_available += db_response.meta.data_available
        if not more_data_available:
            more_data_available = db_response.meta.more_data_available

        for datum in db_response.data:
            dumped_datum = datum.model_dump(exclude_unset=True, exclude_none=True)
            dumped_datum["id"] = f"{database['id']}/{dumped_datum['id']}"
            data.append(dumped_datum)

    assert data_returned == response.meta.data_returned
    assert data_available == response.meta.data_available
    assert more_data_available == response.meta.more_data_available

    print(response.data[0])

    assert data == response.model_dump(exclude_unset=True, exclude_none=True)["data"], (
        "IDs in test not in response: "
        f"{ {_['id'] for _ in data} - {_['id'] for _ in response.model_dump(exclude_unset=True)['data']} }\n\n"  # noqa: E501
        "IDs in response not in test: "
        f"{ {_['id'] for _ in response.model_dump(exclude_unset=True)['data']} - {_['id'] for _ in data} }\n\n"  # noqa: E501
        f"A /search datum: {response.model_dump(exclude_unset=True)['data'][0]}\n\n"
        f"A retrieved datum: "
        f"{next(_ for _ in data if _['id'] == response.model_dump(exclude_unset=True)['data'][0]['id'])}"  # noqa: E501
    )

    assert "A gateway was found and reused for a query" in caplog.text, caplog.text
    assert "A new gateway was created for a query" not in caplog.text, caplog.text


async def test_post_search(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
    top_dir: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test POST /search

    By using the gateway "twodbs", but adding the versioned part to the base URL,
    this should ensure a new gateway is created, specifically for use with these
    versioned base URLs, but we can reuse the mock_gateway_responses for the "twodbs"
    gateway.
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
            f'{_.get("attributes", {}).get("base_url").rstrip("/")}/v1'
            for _ in gateway.get("databases", [{}])
        ],
    }

    mock_gateway_responses(gateway)

    response = await client("/search", method="post", json=data)

    assert response.status_code == 202, f"Request failed: {response.json()}"

    response = QueriesResponseSingle(**response.json())
    assert response

    assert getattr(
        response.meta, f"_{CONFIG.provider.prefix}_created"
    ), response.meta.model_dump()

    assert "A new gateway was created for a query" in caplog.text, caplog.text
    assert "A gateway was found and reused for a query" not in caplog.text, caplog.text

    datum = response.data
    assert datum, response

    assert (
        datum.attributes.query_parameters.model_dump()
        == OptimadeQueryParameters(**data["query_parameters"]).model_dump()
    ), (
        f"Response: {datum.attributes.query_parameters!r}\n\n"
        f"Test data: {OptimadeQueryParameters(**data['query_parameters'])!r}"
    )

    assert datum.attributes.state in [QueryState.CREATED, QueryState.STARTED]
    assert datum.attributes.response is None

    gateways = json.loads(
        (top_dir / "tests" / "static" / "test_gateways.json").read_text()
    )

    assert datum.attributes.gateway_id not in [_["id"] for _ in gateways]

    mongo_filter = {"id": {"$eq": datum.id}}
    assert await MONGO_DB["queries"].count_documents(mongo_filter) == 1

    await asyncio.sleep(1)  # Ensure mock URL is queried


async def test_post_search_existing_gateway(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test POST /search for base URLs matching an existing gateway"""
    import asyncio

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.queries import OptimadeQueryParameters, QueryState
    from optimade_gateway.models.responses import QueriesResponseSingle
    from optimade_gateway.mongo.database import MONGO_DB

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    data = [
        # optimade_urls
        {
            "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 15},
            "optimade_urls": [
                _.get("attributes", {}).get("base_url")
                for _ in gateway.get("databases", [{}])
            ],
        },
        # database_ids
        {
            "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 15},
            "database_ids": [_.get("id") for _ in gateway.get("databases", [{}])],
        },
        # Both optimade_urls & database_ids
        {
            "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 15},
            "database_ids": [gateway.get("databases", [{}])[0].get("id")],
            "optimade_urls": [
                gateway.get("databases", [{}])[-1].get("attributes", {}).get("base_url")
            ],
        },
    ]

    mock_gateway_responses(gateway)

    for gateway_create_data in data:
        response = await client("/search", method="post", json=gateway_create_data)

        assert response.status_code == 202, f"Request failed: {response.json()}"

        response = QueriesResponseSingle(**response.json())
        assert response

        await asyncio.sleep(1)  # Ensure the query finishes

        assert getattr(
            response.meta, f"_{CONFIG.provider.prefix}_created"
        ), response.meta.model_dump()

        assert "A gateway was found and reused for a query" in caplog.text, caplog.text
        assert "A new gateway was created for a query" not in caplog.text, caplog.text

        datum = response.data
        assert datum, response

        assert (
            datum.attributes.query_parameters.model_dump()
            == OptimadeQueryParameters(
                **gateway_create_data["query_parameters"]
            ).model_dump()
        ), (
            f"Response: {datum.attributes.query_parameters!r}\n\nTest data: "
            f"{OptimadeQueryParameters(**gateway_create_data['query_parameters'])!r}"
        )

        assert datum.attributes.state in [QueryState.CREATED, QueryState.STARTED]
        assert datum.attributes.response is None

        assert datum.attributes.gateway_id == gateway_id

        mongo_filter = {"id": {"$eq": datum.id}}
        assert await MONGO_DB["queries"].count_documents(mongo_filter) == 1


async def test_sort_no_effect(
    client: AsyncGatewayClient,
    get_gateway: GetGateway,
    mock_gateway_responses: MockGatewayResponses,
) -> None:
    """Test GET and POST /search with the `sort` query parameter

    Currently, the `sort` query parameter should not have an effect when used with this
    endpoint. This means if the `sort` parameter is used, the response should not
    change - it should be ignored.
    """
    from optimade.models import Warnings

    from optimade_gateway.models.responses import QueriesResponseSingle
    from optimade_gateway.warnings import SortNotSupported

    gateway_id = "twodbs"
    gateway: dict = await get_gateway(gateway_id)

    query_params_asc = {
        "sort": "id",
        "optimade_urls": [
            f'{_.get("attributes", {}).get("base_url").rstrip("/")}/v1'
            for _ in gateway.get("databases", [{}])
        ],
    }
    query_params_desc = query_params_asc.copy()
    query_params_desc["sort"] = "-id"

    mock_gateway_responses(gateway)

    with pytest.warns(SortNotSupported):
        response_asc = await client("/search", params=query_params_asc)
    with pytest.warns(SortNotSupported):
        response_desc = await client("/search", params=query_params_desc)

    assert response_asc.status_code == 200, f"Request failed: {response_asc.json()}"
    assert response_desc.status_code == 200, f"Request failed: {response_desc.json()}"

    response_asc = QueriesResponseSingle(**response_asc.json())
    assert response_asc
    response_desc = QueriesResponseSingle(**response_desc.json())
    assert response_desc

    assert (
        response_asc.data.attributes.response.data
        == response_desc.data.attributes.response.data
    )

    sort_warning = SortNotSupported()

    for response in (response_asc, response_desc):
        assert response.meta.warnings, response.model_dump_json()
        assert len(response.meta.warnings) == 1
        assert response.meta.warnings[0] == Warnings(
            title=sort_warning.title,
            detail=sort_warning.detail,
        )

    query_params_post_asc = query_params_asc.copy()
    query_params_post_asc["query_parameters"] = {
        "sort": query_params_post_asc.pop("sort")
    }
    query_params_post_desc = query_params_desc.copy()
    query_params_post_desc["query_parameters"] = {
        "sort": query_params_post_desc.pop("sort")
    }

    with pytest.warns(SortNotSupported):
        response_asc = await client(
            "/search", method="post", json=query_params_post_asc
        )
    with pytest.warns(SortNotSupported):
        response_desc = await client(
            "/search", method="post", json=query_params_post_desc
        )

    assert response_asc.status_code == 202, f"Request failed: {response_asc.json()}"
    assert response_desc.status_code == 202, f"Request failed: {response_desc.json()}"

    response_asc = QueriesResponseSingle(**response_asc.json())
    assert response_asc
    response_desc = QueriesResponseSingle(**response_desc.json())
    assert response_desc

    sort_warning = SortNotSupported()

    for response in (response_asc, response_desc):
        assert response.meta.warnings, response.model_dump_json()
        assert len(response.meta.warnings) == 1
        assert response.meta.warnings[0] == Warnings(
            title=sort_warning.title,
            detail=sort_warning.detail,
        )


async def test_get_search_not_finishing(
    client: AsyncGatewayClient,
    mock_gateway_responses: MockGatewayResponses,
    get_gateway: GetGateway,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test GET /search for unfinished query (redirect to query URL)"""
    from optimade_gateway.models.queries import GatewayQueryResponse, QueryState
    from optimade_gateway.models.responses import QueriesResponseSingle

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

    mock_gateway_responses(gateway)

    response = await client("/search", params=query_params)
    assert response.status_code == 200, f"Request failed: {response.json()}"

    assert "A gateway was found and reused for a query" in caplog.text, caplog.text
    assert "A new gateway was created for a query" not in caplog.text, caplog.text

    response = QueriesResponseSingle(**response.json())
    assert (
        response.data.attributes.response.data == {}
    ), f"Data was found in response: {response.model_dump_json(indent=2)}"

    query = response.data
    assert query, query
    assert query.attributes.state in (QueryState.STARTED, QueryState.IN_PROGRESS), query
    assert query.attributes.query_parameters.filter == query_params["filter"], query
    assert (
        query.attributes.query_parameters.page_limit == query_params["page_limit"]
    ), query
    assert isinstance(query.attributes.response, GatewayQueryResponse)
    assert query.attributes.response.data == {}
    assert query.attributes.response.errors == []
    assert query.attributes.gateway_id == gateway_id, query
