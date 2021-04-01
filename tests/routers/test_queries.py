"""Tests for /queries endpoints"""
# pylint: disable=import-error,no-name-in-module
from pathlib import Path

import pytest


pytestmark = pytest.mark.asyncio


async def test_get_queries(client, top_dir: Path):
    """Test GET /queries"""
    import json

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
async def test_post_queries(client):
    """Test POST /queries"""
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
        "endpoint": "structures",
        "endpoint_model": ["optimade.models.responses", "StructureResponseMany"],
    }

    response = await client("/queries", method="post", json=data)

    assert response.status_code == 200, f"Request failed: {response.json()}"
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


@pytest.mark.usefixtures("reset_db_after")
async def test_post_queries_bad_data(client):
    """Test POST /queries with bad data"""
    from optimade.models import ErrorResponse, OptimadeError

    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION

    data = {
        "gateway_id": "non-existent",
        "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 5},
        "endpoint": "structures",
        "endpoint_model": ("optimade.models.responses", "StructureResponseMany"),
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
