"""Tests for /databases endpoints"""
# pylint: disable=no-name-in-module
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


async def test_get_databases(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    top_dir: Path,
):
    """Test GET /databases"""
    import json

    from optimade_gateway.models.responses import DatabasesResponse

    response = await client("/databases")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = DatabasesResponse(**response.json())
    assert response

    with open(top_dir / "tests/static/test_databases.json") as handle:
        test_data = json.load(handle)

    assert response.meta.data_returned == len(test_data)
    assert response.meta.data_available == len(test_data)
    assert not response.meta.more_data_available


@pytest.mark.usefixtures("reset_db_after")
async def test_post_databases(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ]
):
    """Test POST /databases"""
    from bson.objectid import ObjectId
    from optimade.server.routers.utils import BASE_URL_PREFIXES
    from pydantic import AnyUrl

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models.responses import DatabasesResponseSingle
    from optimade_gateway.mongo.database import MONGO_DB

    data = {
        "name": "PyTest test_post_databases",
        "base_url": "https://example.org/test",
    }

    response = await client("/databases", method="post", json=data)

    assert response.status_code == 200, f"Request failed: {response.json()}"
    url = response.url

    response = DatabasesResponseSingle(**response.json())
    assert response

    assert getattr(
        response.meta, f"_{CONFIG.provider.prefix}_created"
    ), response.meta.dict()

    datum = response.data
    assert datum, response

    for field in data:
        assert (
            getattr(response.data.attributes, field) == data[field]
        ), f"Response: {response.data.attributes.dict()!r}\n\nTest data: {data!r}"
    assert datum.links.dict() == {
        "self": AnyUrl(
            url=f"{'/'.join(str(url).split('/')[:-1])}{BASE_URL_PREFIXES['major']}/databases/{datum.id}",
            scheme=url.scheme,
            host=url.host,
        )
    }

    mongo_filter = {"_id": ObjectId(datum.id)}
    assert await MONGO_DB["databases"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["databases"].find_one(mongo_filter)
    for field in data:
        assert db_datum[field] == data[field]


async def test_get_single_database(
    client: Callable[
        [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
        Awaitable[httpx.Response],
    ],
    top_dir: Path,
):
    """Test GET /databases/{id}"""
    import json
    from optimade.server.routers.utils import BASE_URL_PREFIXES
    from pydantic import AnyUrl

    from optimade_gateway.common.utils import clean_python_types
    from optimade_gateway.models.responses import DatabasesResponseSingle
    from optimade_gateway.mongo.database import MONGO_DB

    database_id = "mcloud/optimade-sample"

    response = await client(f"/databases/{database_id}")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    url = response.url

    response = DatabasesResponseSingle(**response.json())
    assert response

    datum = response.data
    assert datum, response

    with open(top_dir / "tests/static/test_databases.json") as handle:
        all_test_data = json.load(handle)
    for data in all_test_data:
        if data["id"] == database_id:
            test_data = data
            break
    else:
        pytest.fail(
            f"Could not find expected test database in test data. ID: {database_id!r}"
        )

    for field in test_data:
        if field in ("id", "type", "links", "relationships", "meta"):
            continue
        assert (
            await clean_python_types(response.data.attributes.dict()[field])
            == data[field]
        ), f"Field: {field!r}\n\nResponse: {response.data.attributes.dict()!r}\n\nTest data: {data!r}"
    test_links = {
        "self": AnyUrl(
            url=f"{'/'.join(str(url).split('/')[:-3])}{BASE_URL_PREFIXES['major']}/databases/{datum.id}",
            scheme=url.scheme,
            host=url.host,
        )
    }
    assert (
        datum.links.dict() == test_links
    ), f"Response: {datum.links.dict()}\n\nTest data: {test_links}"

    mongo_filter = {"id": datum.id}
    assert await MONGO_DB["databases"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["databases"].find_one(mongo_filter)
    for field in test_data:
        assert db_datum[field] == data[field]
