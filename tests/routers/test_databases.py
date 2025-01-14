"""Tests for /databases endpoints"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from ..conftest import AsyncGatewayClient


async def test_get_databases(
    client: AsyncGatewayClient,
    top_dir: Path,
) -> None:
    """Test GET /databases"""
    import json

    from optimade_gateway.models.responses import DatabasesResponse

    response = await client("/databases")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = DatabasesResponse(**response.json())
    assert response

    test_data = json.loads(
        (top_dir / "tests" / "static" / "test_databases.json").read_text()
    )

    assert response.meta.data_returned == len(test_data)
    assert response.meta.data_available == len(test_data)
    assert not response.meta.more_data_available


async def test_post_databases(client: AsyncGatewayClient) -> None:
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
    ), response.meta.model_dump()

    datum = response.data
    assert datum, response

    for field, field_value in data.items():
        value = getattr(response.data.attributes, field)
        if isinstance(value, AnyUrl):
            assert str(value) == field_value, (
                f"Response: {response.data.attributes.model_dump()!r}\n\n"
                f"Test data: {data!r}"
            )
        else:
            assert value == field_value, (
                f"Response: {response.data.attributes.model_dump()!r}\n\n"
                f"Test data: {data!r}"
            )
    assert datum.links.model_dump() == {
        "self": str(
            AnyUrl(
                f"{'/'.join(str(url).split('/')[:-1])}"
                f"{BASE_URL_PREFIXES['major']}/databases/{datum.id}"
            )
        )
    }

    mongo_filter = {"_id": ObjectId(datum.id)}
    assert await MONGO_DB["databases"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["databases"].find_one(mongo_filter)
    for field, field_value in data.items():
        assert (
            db_datum[field] == field_value
        ), f"Response: {db_datum!r}\n\nTest data: {data!r}"


async def test_get_single_database(
    client: AsyncGatewayClient,
    top_dir: Path,
) -> None:
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

    all_test_data = json.loads(
        (top_dir / "tests" / "static" / "test_databases.json").read_text()
    )

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
            await clean_python_types(response.data.attributes.model_dump()[field])
            == data[field]
        ), (
            "Field: "
            f"{field!r}\n\nResponse: {response.data.attributes.model_dump()!r}\n\n"
            f"Test data: {data!r}"
        )
    test_links = {
        "self": str(
            AnyUrl(
                f"{'/'.join(str(url).split('/')[:-3])}{BASE_URL_PREFIXES['major']}"
                f"/databases/{datum.id}"
            )
        )
    }
    assert (
        datum.links.model_dump() == test_links
    ), f"Response: {datum.links.model_dump()}\n\nTest data: {test_links}"

    mongo_filter = {"id": datum.id}
    assert await MONGO_DB["databases"].count_documents(mongo_filter) == 1
    db_datum = await MONGO_DB["databases"].find_one(mongo_filter)
    for field in test_data:
        assert db_datum[field] == data[field]
