"""Tests for /gateways endpoints"""
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from ..conftest import AsyncGatewayClient


async def test_get_gateways(
    client: "AsyncGatewayClient",
    top_dir: "Path",
) -> None:
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
async def test_post_gateways(client: "AsyncGatewayClient") -> None:
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


async def test_path_id_raises(
    client: "AsyncGatewayClient",
    top_dir: "Path",
) -> None:
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


async def test_post_gateways_database_ids(client: "AsyncGatewayClient") -> None:
    """Test POST /gateways with `database_ids` specified"""
    from optimade.server.routers.utils import BASE_URL_PREFIXES
    from pydantic import AnyUrl

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.responses import GatewaysResponseSingle
    from optimade_gateway.mongo.database import MONGO_DB

    # Databases for gateway "twodbs"
    data = {"database_ids": ["mcloud/mc2d", "mcloud/optimade-sample"]}

    response = await client("/gateways", method="post", json=data)

    assert response.status_code == 200, f"Request failed: {response.json()}"
    url = response.url

    response = GatewaysResponseSingle(**response.json())
    assert response

    assert not getattr(
        response.meta, f"_{CONFIG.provider.prefix}_created"
    ), response.meta.dict()

    datum = response.data
    assert datum, response

    assert datum.id == "twodbs"
    for database in datum.attributes.databases:
        assert database.id in data["database_ids"]

    assert datum.links.dict() == {
        "self": AnyUrl(
            url=f"{'/'.join(str(url).split('/')[:-1])}{BASE_URL_PREFIXES['major']}/gateways/{datum.id}",
            scheme=url.scheme,
            host=url.host,
        )
    }

    mongo_filter = {"id": datum.id}
    assert await MONGO_DB["gateways"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["gateways"].find_one(mongo_filter)
    for db in db_datum["databases"]:
        assert db["id"] in data["database_ids"]


@pytest.mark.usefixtures("reset_db_after")
async def test_post_gateways_create_with_db_ids(client: "AsyncGatewayClient") -> None:
    """Test POST /gateways with `database_ids`, while creating gateway"""
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
        ],
        "database_ids": ["mcloud/mc2d"],
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

    for database in datum.attributes.databases:
        assert database.id in [data["databases"][0]["id"], data["database_ids"][0]]

    assert datum.links.dict() == {
        "self": AnyUrl(
            url=f"{'/'.join(str(url).split('/')[:-1])}{BASE_URL_PREFIXES['major']}/gateways/{datum.id}",
            scheme=url.scheme,
            host=url.host,
        )
    }

    mongo_filter = {"id": datum.id}
    assert await MONGO_DB["gateways"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["gateways"].find_one(mongo_filter)
    for db in db_datum["databases"]:
        assert db["id"] in [data["databases"][0]["id"], data["database_ids"][0]]


async def test_get_single_gateway(
    client: "AsyncGatewayClient",
    random_gateway: str,
    top_dir: "Path",
) -> None:
    """Test GET /gateways/{gateway_id}"""
    import json

    from optimade_gateway.models.responses import GatewaysResponseSingle

    response = await client(f"/gateways/{random_gateway}")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = GatewaysResponseSingle(**response.json())
    assert response

    with open(top_dir / "tests/static/test_gateways.json") as handle:
        test_data = json.load(handle)

    assert response.meta.data_returned == 1
    assert response.meta.data_available == len(test_data)
    assert not response.meta.more_data_available
