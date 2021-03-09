"""Tests for /queries endpoints"""
# pylint: disable=import-error,no-name-in-module
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_queries(client):
    """Test GET /queries"""
    from optimade_gateway.models.responses import QueriesResponse

    response = await client("/queries")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = QueriesResponse(**response.json())
    assert response

    assert response.meta.data_returned == 3
    assert response.meta.data_available == 3
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
        "types": ["structures"],
        "gateway_id": "singledb",
        "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 5},
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

    # Remove it and assert it has been removed
    await MONGO_DB["queries"].delete_one(mongo_filter)
    assert await MONGO_DB["queries"].count_documents(mongo_filter) == 0
    assert await MONGO_DB["queries"].count_documents({}) == 3


@pytest.mark.usefixtures("reset_db_after")
async def test_post_queries_bad_data(client):
    """Test POST /queries with bad data"""
    from optimade.models import ErrorResponse, OptimadeError

    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION

    data = {
        "types": ["structures"],
        "gateway_id": "non-existent",
        "query_parameters": {"filter": 'elements HAS "Cu"', "page_limit": 5},
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
