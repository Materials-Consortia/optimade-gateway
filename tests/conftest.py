"""Pytest fixtures and configuration for all tests"""
# pylint: disable=import-error
import asyncio
import json
import os
from pathlib import Path
from typing import Callable

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

import pytest


def pytest_configure(config):
    """Method that runs before pytest collects tests so no modules are imported"""
    cwd = Path(__file__).parent.resolve()
    os.environ["OPTIMADE_GATEWAY_CONFIG_FILE"] = str(cwd / "static/test_config.json")
    os.environ["OPTIMADE_CONFIG_FILE"] = str(cwd / "static/test_config.json")
    os.environ["OPTIMADE_CI_FORCE_MONGO"] = "1"


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
    from optimade_gateway.mongo.database import MONGO_DB

    with open(top_dir.joinpath("tests/static/test_config.json")) as handle:
        test_db_name = json.load(handle)["mongo_database"]
    assert MONGO_DB.name == test_db_name, "Test DB has not been loaded!"

    for collection in ("gateways",):
        await MONGO_DB[collection].drop()

        with open(top_dir.joinpath(f"tests/static/test_{collection}.json")) as handle:
            data = json.load(handle)

        await MONGO_DB[collection].insert_many(data)


@pytest.fixture
def client() -> Callable:
    """Return function to make HTTP requests with async httpx client"""
    from fastapi import FastAPI
    from httpx import AsyncClient, Response

    async def _client(
        request: str,
        app: FastAPI = None,
        base_url: str = None,
        method: Literal["get", "post", "put", "delete", "patch"] = None,
        **kwargs,
    ) -> Response:
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
def get_gateway() -> Callable:
    """Return function to find a single gateway in the current MongoDB"""

    async def _get_gateway(id: str) -> dict:
        """Get a gateway that's currently in the MongoDB"""
        from optimade_gateway.mongo.database import MONGO_DB

        return await MONGO_DB["gateways"].find_one({"id": id})

    return _get_gateway
