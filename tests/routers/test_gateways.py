"""Tests for /gateways endpoints"""
# pylint: disable=import-error,no-name-in-module
from pathlib import Path

import pytest


pytestmark = pytest.mark.asyncio


async def test_get_gateways(client, top_dir: Path):
    """Test GET /gateways"""
    import json

    from optimade_gateway.models.responses import GatewaysResponse

    response = await client("/gateways")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = GatewaysResponse(**response.json())
    assert response

    with open(top_dir / "tests/static/test_gateways.json") as handle:
        test_data = json.load(handle)

    assert response.meta.data_returned == len(test_data)
    assert response.meta.data_available == len(test_data)
    assert not response.meta.more_data_available


@pytest.mark.usefixtures("reset_db_after")
async def test_post_gateways(client):
    """Test POST /gateways"""
    from bson.objectid import ObjectId
    from optimade.models import LinksResource
    from optimade.server.routers.utils import BASE_URL_PREFIXES
    from pydantic import AnyUrl

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.responses import GatewaysResponseSingle
    from optimade_gateway.mongo.database import MONGO_DB

    data = {
        "databases": [
            {
                "id": "test_post_gateways",
                "type": "links",
                "attributes": {
                    "name": "PyTest test_post_gateways",
                    "description": "This is a valid test database",
                    "base_url": "https://example.org/test",
                    "homepage": "https://example.org",
                    "link_type": "child",
                },
            }
        ]
    }

    response = await client("/gateways", method="post", json=data)

    assert response.status_code == 200, f"Request failed: {response.json()}"
    url = response.url

    response = GatewaysResponseSingle(**response.json())
    assert response

    assert getattr(
        response.meta, f"_{CONFIG.provider.prefix}_created"
    ), response.meta.dict()

    datum = response.data
    assert datum, response

    for response_db, test_db in zip(datum.attributes.databases, data["databases"]):
        assert (
            response_db.dict() == LinksResource(**test_db).dict()
        ), f"Response: {response_db!r}\n\nTest data: {LinksResource(**test_db)!r}"
    assert datum.links.dict() == {
        "self": AnyUrl(
            url=f"{'/'.join(str(url).split('/')[:-1])}{BASE_URL_PREFIXES['major']}/gateways/{datum.id}",
            scheme=url.scheme,
            host=url.host,
        )
    }

    mongo_filter = {"_id": ObjectId(datum.id)}
    assert await MONGO_DB["gateways"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["gateways"].find_one(mongo_filter)
    assert db_datum["databases"] == data["databases"]


async def test_path_id_raises(client, top_dir: Path):
    """Ensure a suggested gateway id with a forward slash gives an error"""
    import json

    from optimade_gateway.mongo.database import MONGO_DB

    bad_gateway_id = "path/id"

    response = await client(
        "/gateways", method="post", json={"id": bad_gateway_id, "databases": []}
    )

    assert (
        response.status_code == 400
    ), f"Request succeeded, where it should've failed: {response.json()}"

    mongo_filter = {"id": bad_gateway_id}
    assert await MONGO_DB["gateways"].count_documents(mongo_filter) == 0

    with open(top_dir / "tests/static/test_gateways.json") as handle:
        test_data = json.load(handle)

    assert await MONGO_DB["gateways"].count_documents({}) == len(test_data)
