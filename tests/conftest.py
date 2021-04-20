"""Pytest fixtures and configuration for all tests"""
# pylint: disable=import-error
import asyncio
import json
import os
from pathlib import Path
import re
from typing import Awaitable, Callable, Union

from fastapi import FastAPI
import httpx
import pytest
from pytest_httpx import HTTPXMock, to_response
from pytest_httpx._httpx_internals import Response as MockResponse

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


# UTILITY FUNCTIONS


async def setup_db_utility(top_dir: Union[Path, str]) -> None:
    """Utility function for setting up/resetting the MongoDB

    Parameters:
        top_dir: Path to the repository's directory.

    """
    from optimade_gateway.mongo.database import MONGO_DB

    top_dir = Path(top_dir).resolve()

    with open(top_dir.joinpath("tests/static/test_config.json")) as handle:
        test_config = json.load(handle)
    assert (
        MONGO_DB.name == test_config["mongo_database"]
    ), "Test DB has not been loaded!"

    for resource in ("databases", "gateways", "links", "queries"):
        collection = test_config.get(f"{resource}_collection", resource)
        await MONGO_DB[collection].drop()

        data_file = top_dir.joinpath(f"tests/static/test_{resource}.json")
        assert (
            data_file.exists()
        ), f"Test data file at {data_file} does not seem to exist!"

        with open(data_file) as handle:
            data = json.load(handle)

        await MONGO_DB[collection].insert_many(data)


# PYTEST FIXTURES AND CONFIGURATION


def pytest_configure(config):
    """Method that runs before pytest collects tests so no modules are imported"""
    cwd = Path(__file__).parent.resolve()
    os.environ["OPTIMADE_CONFIG_FILE"] = str(cwd / "static/test_config.json")


@pytest.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def top_dir() -> Path:
    """Return Path instance for the repository's top (root) directory"""
    return Path(__file__).parent.parent.resolve()


@pytest.fixture(scope="session", autouse=True)
async def setup_db(top_dir: Path) -> None:
    """Setup test DB"""
    await setup_db_utility(top_dir)


@pytest.fixture
def client() -> Callable[
    [str, FastAPI, str, Literal["get", "post", "put", "delete", "patch"]],
    httpx.Response,
]:
    """Return function to make HTTP requests with async httpx client"""
    from httpx import AsyncClient

    async def _client(
        request: str,
        app: FastAPI = None,
        base_url: str = None,
        method: Literal["get", "post", "put", "delete", "patch"] = None,
        **kwargs,
    ) -> httpx.Response:
        """Perform async HTTP request

        Parameters:
            request: URL path with query parameters

        """
        from optimade_gateway.main import APP
        from optimade_gateway.common.config import CONFIG

        app = app if app is not None else APP
        base_url = base_url if base_url is not None else CONFIG.base_url
        method = method if method is not None else "get"

        async with AsyncClient(app=app, base_url=base_url) as aclient:
            response = await getattr(aclient, method)(request, **kwargs)

        return response

    return _client


@pytest.fixture
def get_gateway() -> Callable[[str], Awaitable[dict]]:
    """Return function to find a single gateway in the current MongoDB"""

    async def _get_gateway(id: str) -> dict:
        """Get a gateway that's currently in the MongoDB"""
        from optimade_gateway.mongo.database import MONGO_DB

        return await MONGO_DB["gateways"].find_one({"id": id})

    return _get_gateway


@pytest.fixture
async def reset_db_after(top_dir: Path) -> None:
    """Reset MongoDB with original test data after the test has run"""
    try:
        yield
    finally:
        # Reset MongoDB
        await setup_db_utility(top_dir)


@pytest.fixture
def mock_gateway_responses(
    httpx_mock: HTTPXMock, top_dir: Path
) -> Callable[[dict], None]:
    """Add mock responses for gateway databases

    (Successful) mock responses are loaded from local JSON files and returned according to the
    database id.

    """

    def _mock_response(gateway: dict) -> None:
        """Add mock responses (`httpx_mock`) for `gateway`'s databases"""
        for database in gateway["databases"]:
            if database["id"].startswith("sleep"):
                httpx_mock.add_callback(
                    callback=sleep_response,
                    url=re.compile(fr"{database['attributes']['base_url']}.*"),
                )
            else:
                with open(
                    top_dir / f"tests/static/db_responses/{database['id']}.json"
                ) as handle:
                    data = json.load(handle)
                httpx_mock.add_response(
                    url=re.compile(fr"{database['attributes']['base_url']}.*"),
                    json=data,
                )

    def sleep_response(request: httpx.Request, ext: dict) -> MockResponse:
        """A mock response from an external OPTIMADE DB URL

        This response sleeps for X seconds, where X is derived from the database ID.
        """
        from concurrent.futures import ThreadPoolExecutor
        import time

        sleep_arg = int(request.url.host.split("-")[-1])

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.map(time.sleep, [sleep_arg])
        with open(top_dir / "tests/static/db_responses/optimade-sample.json") as handle:
            data = json.load(handle)
        return to_response(json=data)

    return _mock_response


@pytest.fixture
def non_mocked_hosts() -> list:
    return ["example.org"]
