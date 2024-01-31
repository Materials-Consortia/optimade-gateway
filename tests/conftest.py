"""Pytest fixtures and configuration for all tests"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from typing import Literal, Protocol, TypedDict

    from fastapi import FastAPI
    from httpx import Request, Response
    from pymongo.database import Database
    from pytest_httpx import HTTPXMock

    class AsyncGatewayClient(Protocol):
        """Protocol for async client fixture"""

        def __call__(
            self,
            request: str,
            app: FastAPI | None = None,
            base_url: str | None = None,
            method: Literal["get", "post", "put", "delete", "patch"] | None = None,
            **kwargs,
        ) -> Awaitable[Response]: ...

    class GetGateway(Protocol):
        """Protocol for get_gateway fixture"""

        def __call__(self, id: str) -> Awaitable[dict]: ...

    class MockGatewayResponses(Protocol):
        """Protocol for mock_gateway_responses fixture"""

        def __call__(self, gateway: dict) -> None: ...

    class DatabaseAttributesOptionalsDict(TypedDict, total=False):
        """Database attributes dict of optional fields"""

        aggregate: str

    class DatabaseAttributesDict(DatabaseAttributesOptionalsDict):
        """Database attributes dict"""

        name: str
        description: str
        base_url: str
        homepage: str | None
        link_type: str

    class DatabaseDict(TypedDict):
        """Database dict"""

        id: str
        type: str
        attributes: DatabaseAttributesDict

    class GatewayDict(TypedDict):
        """Gateway dict"""

        id: str
        last_modified: str
        databases: list[DatabaseDict]


# UTILITY FUNCTIONS

MONGO_DB_INFO: tuple[Database, bool] | None = None


def get_test_config(top_dir: Path | str) -> dict:
    """Utility function for getting and parsing the test config."""
    top_dir = Path(top_dir).resolve()

    test_config: dict = json.loads(
        (top_dir / "tests" / "static" / "test_config.json").read_bytes()
    )

    assert isinstance(test_config, dict), "Test config is not a dict!"

    return test_config


def get_mongo_db(top_dir: Path | str) -> tuple[Database, bool]:
    """Utility function for getting the MongoDB"""
    global MONGO_DB_INFO  # noqa: PLW0603
    test_config = get_test_config(top_dir)

    if MONGO_DB_INFO is not None:
        return MONGO_DB_INFO

    if any(
        _ == "mongodb"
        for _ in (
            os.getenv("OPTIMADE_DATABASE_BACKEND"),
            test_config["database_backend"],
        )
    ):
        from optimade_gateway.mongo.database import MONGO_DB

        mock_client = False
    else:
        from mongomock_motor import AsyncMongoMockClient

        from optimade_gateway.common.config import CONFIG

        MONGO_DB = AsyncMongoMockClient(
            host=CONFIG.mongo_uri,
            appname="optimade-gateway",
            readConcernLevel="majority",
            readPreference="primary",
            w="majority",
        )[test_config["mongo_database"]]

        mock_client = True

    MONGO_DB_INFO = MONGO_DB, mock_client

    return MONGO_DB_INFO


async def setup_db_utility(top_dir: Path | str) -> None:
    """Utility function for setting up/resetting the MongoDB

    Parameters:
        top_dir: Path to the repository's directory.

    """
    top_dir = Path(top_dir).resolve()
    test_config = get_test_config(top_dir)
    MONGO_DB, _ = get_mongo_db(top_dir)

    assert (
        MONGO_DB.name == test_config["mongo_database"]
    ), "Test DB has not been loaded!"

    for resource in ("databases", "gateways", "links", "queries"):
        collection = test_config.get(f"{resource}_collection", resource)
        await MONGO_DB[collection].drop()

        data_file = top_dir / "tests" / "static" / f"test_{resource}.json"

        assert (
            data_file.exists()
        ), f"Test data file at {data_file} does not seem to exist!"

        data: list[dict] = json.loads(data_file.read_bytes())

        await MONGO_DB[collection].insert_many(data)


# PYTEST FIXTURES AND CONFIGURATION


def pytest_configure(config):  # noqa: ARG001
    """Method that runs before pytest collects tests so no modules are imported"""
    cwd = Path(__file__).parent.resolve()
    os.environ["OPTIMADE_CONFIG_FILE"] = str(cwd / "static/test_config.json")


@pytest.fixture(scope="session")
def event_loop(request):  # noqa: ARG001
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def top_dir() -> Path:
    """Return Path instance for the repository's top (root) directory"""
    return Path(__file__).parent.parent.resolve()


@pytest.fixture(scope="session", autouse=True)
async def _setup_db(top_dir: Path) -> None:
    """Setup test DB"""
    await setup_db_utility(top_dir)


@pytest.fixture(autouse=True)
def _patch_mongo_db(top_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Return test config dict"""
    MONGO_DB, mock_client = get_mongo_db(top_dir)

    if mock_client:
        from optimade_gateway.mongo import database

        monkeypatch.setattr(database, "MONGO_DB", MONGO_DB)


@pytest.fixture()
def client() -> AsyncGatewayClient:
    """Return function to make HTTP requests with async httpx client"""
    from httpx import AsyncClient

    async def _client(
        request: str,
        app: FastAPI | None = None,
        base_url: str | None = None,
        method: Literal["get", "post", "put", "delete", "patch"] | None = None,
        **kwargs,
    ) -> Response:
        """Perform async HTTP request

        Parameters:
            request: URL path with query parameters

        """
        from optimade_gateway.common.config import CONFIG
        from optimade_gateway.main import APP

        app = app if app is not None else APP
        base_url = base_url if base_url is not None else CONFIG.base_url
        method = method if method is not None else "get"

        async with AsyncClient(
            app=app, base_url=base_url, follow_redirects=True
        ) as aclient:
            return await getattr(aclient, method)(request, **kwargs)

    return _client


@pytest.fixture()
def get_gateway() -> GetGateway:
    """Return function to find a single gateway in the current MongoDB"""

    async def _get_gateway(id: str) -> dict:
        """Get a gateway that's currently in the MongoDB"""
        from optimade_gateway.mongo.database import MONGO_DB

        return await MONGO_DB["gateways"].find_one({"id": id})

    return _get_gateway


@pytest.fixture()
async def random_gateway() -> dict:
    """Get a random gateway currently in the MongoDB"""
    from optimade_gateway.mongo.database import MONGO_DB

    gateway_ids = set()
    async for gateway in MONGO_DB["gateways"].find(
        filter={}, projection={"id": True, "_id": False}
    ):
        gateway_ids.add(gateway["id"])
    return gateway_ids.pop()


@pytest.fixture(autouse=True)
async def _reset_db_after(top_dir: Path) -> None:
    """Reset MongoDB with original test data after the test has run"""
    try:
        yield
    finally:
        # Reset MongoDB
        await setup_db_utility(top_dir)


@pytest.fixture()
def mock_gateway_responses(
    httpx_mock: HTTPXMock, top_dir: Path
) -> MockGatewayResponses:
    """Add mock responses for gateway databases

    (Successful) mock responses are loaded from local JSON files and returned according
    to the database id.

    """

    def _mock_response(gateway: GatewayDict) -> None:
        """Add mock responses (`httpx_mock`) for `gateway`'s databases"""
        for database in gateway["databases"]:
            if database["id"].startswith("sleep"):
                httpx_mock.add_callback(
                    callback=sleep_response,
                    url=re.compile(rf"{database['attributes']['base_url']}.*"),
                )
            elif (
                gateway["id"].startswith("single-structure")
                and "_single" not in database["id"]
            ):
                # Don't mock database responses for single-structure gateways'
                # databases that are not queried.
                pass
            else:
                data: dict | list = json.loads(
                    (
                        top_dir
                        / "tests"
                        / "static"
                        / "db_responses"
                        / f'{database["id"].split("/", maxsplit=1)[-1]}.json'
                    ).read_bytes()
                )

                if data.get("errors", []):
                    for error in data.get("errors", []):
                        if "status" in error:
                            status_code = int(error["status"])
                            break
                    else:
                        status_code = 500
                else:
                    status_code = 200

                httpx_mock.add_response(
                    url=re.compile(
                        rf"{re.escape(database['attributes']['base_url'])}.*"
                    ),
                    json=data,
                    status_code=status_code,
                )

    def sleep_response(request: Request) -> Response:
        """A mock response from an external OPTIMADE DB URL

        This response sleeps for X seconds, where X is derived from the database ID.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor

        from httpx import Response

        std_response_params = {
            "status_code": 200,
            "extensions": {"http_version": b"HTTP/1.1"},
        }

        sleep_arg = int(request.url.host.split("-")[-1])

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.map(time.sleep, [sleep_arg])

        data = json.loads(
            (
                top_dir / "tests" / "static" / "db_responses" / "optimade-sample.json"
            ).read_bytes()
        )

        return Response(json=data, **std_response_params)

    return _mock_response


@pytest.fixture()
def non_mocked_hosts() -> list:
    return ["example.org"]


@pytest.fixture()
def generic_meta() -> dict:
    """A generic valid OPTIMADE response meta value"""
    return {
        "api_version": "1.0.0",
        "query": {"representation": "/links"},
        "more_data_available": False,
        "schema": "https://schemas.optimade.org/openapi/v1.0.1/optimade.json",
    }
