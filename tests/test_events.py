"""Tests for events.py"""
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Awaitable, Callable

    from pytest_httpx import HTTPXMock


pytestmark = pytest.mark.asyncio


@pytest.mark.usefixtures("reset_db_after")
async def test_ci_dev_startup_ci(caplog: pytest.LogCaptureFixture, top_dir: "Path"):
    """Test ci_dev_startup() if env var CI=true"""
    import json
    import os

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.events import ci_dev_startup
    from optimade_gateway.mongo.database import MONGO_DB

    org_CI = os.getenv("CI")

    try:
        # Set CI environment variable to the same value as in GH Actions
        # Reference: https://docs.github.com/en/actions/reference/environment-variables#default-environment-variables
        os.environ["CI"] = "true"

        # Change current gateway to assure that it is reverted (collection dropped and re-inserted)
        # during `ci_dev_startup()`
        await MONGO_DB[CONFIG.gateways_collection].update_one(
            {"id": "singledb"},
            {"$set": {"databases": []}},
        )
        changed_gateway = await MONGO_DB[CONFIG.gateways_collection].find_one(
            {"id": "singledb"}
        )
        assert changed_gateway["databases"] == []

        await ci_dev_startup()

        assert "CI detected" in caplog.text

        with open(top_dir / ".ci/test_gateways.json") as handle:
            test_data = json.load(handle)

        assert await MONGO_DB[CONFIG.gateways_collection].count_documents({}) == len(
            test_data
        )

        changed_gateway = await MONGO_DB[CONFIG.gateways_collection].find_one(
            {"id": "singledb"}
        )
        assert changed_gateway["databases"] != []
        assert len(changed_gateway["databases"]) == 1

    finally:
        if org_CI is not None:
            os.environ["CI"] = org_CI
        else:
            del os.environ["CI"]


@pytest.mark.usefixtures("reset_db_after")
async def test_ci_dev_startup_dev(caplog: pytest.LogCaptureFixture, top_dir: "Path"):
    """Test ci_dev_startup() if env var OPTIMADE_MONGO_DATABASE=optimade_gateway_dev"""
    import json
    import os

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.events import ci_dev_startup
    from optimade_gateway.mongo.database import MONGO_DB

    org_CI = os.getenv("CI")
    org_env_var = os.getenv("OPTIMADE_MONGO_DATABASE")

    try:
        # Remove "CI" env var to avoid that function execution branch
        if "CI" in os.environ:
            del os.environ["CI"]

        os.environ["OPTIMADE_MONGO_DATABASE"] = "optimade_gateway_dev"

        # Change current gateway to assure that it is reverted (collection dropped and re-inserted)
        # during `ci_dev_startup()`
        await MONGO_DB[CONFIG.gateways_collection].update_one(
            {"id": "singledb"},
            {"$set": {"databases": []}},
        )
        changed_gateway = await MONGO_DB[CONFIG.gateways_collection].find_one(
            {"id": "singledb"}
        )
        assert changed_gateway["databases"] == []

        await ci_dev_startup()

        assert "Running in development mode" in caplog.text

        with open(top_dir / ".ci/test_gateways.json") as handle:
            test_data = json.load(handle)

        assert await MONGO_DB[CONFIG.gateways_collection].count_documents({}) == len(
            test_data
        )

        changed_gateway = await MONGO_DB[CONFIG.gateways_collection].find_one(
            {"id": "singledb"}
        )
        assert changed_gateway["databases"] != []
        assert len(changed_gateway["databases"]) == 1

    finally:
        if org_CI is not None:
            os.environ["CI"] = org_CI
        if org_env_var is not None:
            os.environ["OPTIMADE_MONGO_DATABASE"] = org_env_var
        else:
            del os.environ["OPTIMADE_MONGO_DATABASE"]


@pytest.mark.usefixtures("reset_db_after")
async def test_ci_dev_startup_nothing(caplog: pytest.LogCaptureFixture):
    """Test ci_dev_startup() if not in CI or development mode"""
    import os

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.events import ci_dev_startup
    from optimade_gateway.mongo.database import MONGO_DB

    org_CI = os.getenv("CI")
    org_env_var = os.getenv("OPTIMADE_MONGO_DATABASE")

    try:
        # Remove "CI" and "OPTIMADE_MONGO_DATABASE" env var to avoid those function execution
        # branches
        if "CI" in os.environ:
            del os.environ["CI"]
        if "OPTIMADE_MONGO_DATABASE" in os.environ:
            del os.environ["OPTIMADE_MONGO_DATABASE"]

        # Change current gateway to assure that it is NOT reverted (collection dropped and
        # re-inserted) during `ci_dev_startup()`
        await MONGO_DB[CONFIG.gateways_collection].update_one(
            {"id": "singledb"},
            {"$set": {"databases": []}},
        )
        changed_gateway = await MONGO_DB[CONFIG.gateways_collection].find_one(
            {"id": "singledb"}
        )
        assert changed_gateway["databases"] == []
        number_of_gateways = await MONGO_DB[CONFIG.gateways_collection].count_documents(
            {}
        )

        await ci_dev_startup()

        assert "Not in CI or development mode" in caplog.text

        assert (
            await MONGO_DB[CONFIG.gateways_collection].count_documents({})
            == number_of_gateways
        )

        changed_gateway = await MONGO_DB[CONFIG.gateways_collection].find_one(
            {"id": "singledb"}
        )
        assert changed_gateway["databases"] == []

    finally:
        if org_CI is not None:
            os.environ["CI"] = org_CI
        if org_env_var is not None:
            os.environ["OPTIMADE_MONGO_DATABASE"] = org_env_var


async def test_load_databases_but_dont(caplog: pytest.LogCaptureFixture):
    """Test load_optimade_providers_databases() but with current CONFIG of False"""
    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.events import load_optimade_providers_databases

    assert CONFIG.load_optimade_providers_databases is False

    await load_optimade_providers_databases()

    assert (
        "Will not load databases from Materials-Consortia list of providers."
        in caplog.text
    )


async def test_load_databases_providers_error(
    httpx_mock: "HTTPXMock", caplog: pytest.LogCaptureFixture, top_dir: "Path"
):
    """Test load_optimade_providers_databases() when providers.optimade.org returns != 200"""
    import json
    import re

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.events import load_optimade_providers_databases
    from optimade_gateway.mongo.database import MONGO_DB

    org_val = CONFIG.load_optimade_providers_databases

    httpx_mock.add_response(
        url=re.compile(r"https://providers\.optimade\.org.*"),
        status_code=404,  # Not found
    )

    try:
        CONFIG.load_optimade_providers_databases = True

        number_of_databases = await MONGO_DB[
            CONFIG.databases_collection
        ].count_documents({})
        with open(top_dir / "tests/static/test_databases.json") as handle:
            test_data = json.load(handle)
        assert number_of_databases == len(test_data)

        await load_optimade_providers_databases()

        assert (
            "Response from Materials-Consortia's list of OPTIMADE providers was not successful"
            in caplog.text
        )
        assert (
            "Registering Materials-Consortia list of OPTIMADE providers' databases"
            not in caplog.text
        )

        assert (
            await MONGO_DB[CONFIG.databases_collection].count_documents({})
            == number_of_databases
        )

    finally:
        # Reset CONFIG
        CONFIG.load_optimade_providers_databases = org_val


async def test_load_databases_no_databases(
    httpx_mock: "HTTPXMock", caplog: pytest.LogCaptureFixture, top_dir: "Path"
):
    """Test load_optimade_providers_databases() when all providers have index meta-dbs with no
    valid databases"""
    import json

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.events import load_optimade_providers_databases
    from optimade_gateway.mongo.database import MONGO_DB

    org_val = CONFIG.load_optimade_providers_databases

    with open(top_dir / "tests/static/db_responses/providers_optimade.json") as handle:
        providers_test_data = json.load(handle)

    httpx_mock.add_response(
        url="https://providers.optimade.org/v1/links",
        json=providers_test_data,
    )
    with open(top_dir / "tests/static/db_responses/index_exmpl.json") as handle:
        no_provider_databases_response: dict = json.load(handle)
    for provider in providers_test_data["data"]:
        url = (
            f"{provider['attributes']['base_url'].rstrip('/')}/v1/links"
            if provider["attributes"]["base_url"] is not None
            else None
        )
        if provider["id"] == "mcloud":
            # Standard exmpl response. Contains a single CHILD db with `null` base_url
            httpx_mock.add_response(
                url=url,
                json=no_provider_databases_response,
            )
        elif provider["id"] == "odbx":
            # Modified exmpl response. Contains no CHILD dbs.
            no_child_response = no_provider_databases_response.copy()
            no_child_response["data"] = [
                _
                for _ in no_child_response["data"]
                if _["attributes"]["link_type"] != "child"
            ]
            httpx_mock.add_response(
                url=url,
                json=no_child_response,
            )

    try:
        CONFIG.load_optimade_providers_databases = True

        number_of_databases = await MONGO_DB[
            CONFIG.databases_collection
        ].count_documents({})

        await load_optimade_providers_databases()

        assert (
            "Response from Materials-Consortia's list of OPTIMADE providers was not successful"
            not in caplog.text
        )
        assert (
            "Registering Materials-Consortia list of OPTIMADE providers' databases"
            in caplog.text
        )

        for provider in providers_test_data["data"]:
            if provider["id"] in ("exmpl", "optimade"):
                assert (
                    f"- {provider['attributes']['name']} (id={provider['id']!r}) - Skipping: Not a real provider."
                    in caplog.text
                )
            elif provider["id"] in ("mcloud", "odbx"):
                assert (
                    f"- {provider['attributes']['name']} (id={provider['id']!r}) - Skipping: Not a real provider."
                    not in caplog.text
                )
                assert (
                    f"- {provider['attributes']['name']} (id={provider['id']!r}) - Skipping: No base URL information."
                    not in caplog.text
                )
                assert (
                    f"- {provider['attributes']['name']} (id={provider['id']!r}) - Processing"
                    in caplog.text
                )
            else:
                assert (
                    f"- {provider['attributes']['name']} (id={provider['id']!r}) - Skipping: No base URL information."
                    in caplog.text
                )

        # Since 'mcloud' returns the standard exmpl index meta-db response, there will be a single
        # CHILD db with 'null' base_url
        exmpl_child_db = [
            _ for _ in no_provider_databases_response["data"] if _["id"] == "exmpl"
        ][0]
        assert (
            f"  - {exmpl_child_db['attributes']['name']} (id={exmpl_child_db['id']!r}) - Skipping: No base URL information."
            in caplog.text
        )
        assert (
            f"  - {exmpl_child_db['attributes']['name']} (id={exmpl_child_db['id']!r}) - Checking versioned base URL and /structures"
            not in caplog.text
        )

        # Since there are no CHILD dbs for 'odbx' the "skipping" log message for 'exmpl' shoud only appear once
        assert caplog.text.count("  - No OPTIMADE databases found.") == 1
        assert (
            caplog.text.count(
                f"  - {exmpl_child_db['attributes']['name']} (id={exmpl_child_db['id']!r}) - Skipping: No base URL information."
            )
            == 1
        )

        # No new databases should be added based on the mock responses
        assert (
            await MONGO_DB[CONFIG.databases_collection].count_documents({})
            == number_of_databases
        )

    finally:
        # Reset CONFIG
        CONFIG.load_optimade_providers_databases = org_val


@pytest.mark.usefixtures("reset_db_after")
async def test_load_databases_valid_databases(
    httpx_mock: "HTTPXMock",
    caplog: pytest.LogCaptureFixture,
    top_dir: "Path",
    get_gateway: "Callable[[str], Awaitable[dict]]",
    mock_gateway_responses: "Callable[[dict], None]",
):
    """Test load_optimade_providers_databases() when valid CHILD dbs are found and added"""
    import json

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.events import load_optimade_providers_databases
    from optimade_gateway.mongo.database import MONGO_DB

    org_val = CONFIG.load_optimade_providers_databases

    with open(top_dir / "tests/static/db_responses/providers_optimade.json") as handle:
        providers_test_data = json.load(handle)

    httpx_mock.add_response(
        url="https://providers.optimade.org/v1/links",
        json=providers_test_data,
    )
    for provider in providers_test_data["data"]:
        url = (
            f"{provider['attributes']['base_url'].rstrip('/')}/v1/links"
            if provider["attributes"]["base_url"] is not None
            else None
        )
        if provider["id"] == "mcloud":
            with open(
                top_dir / "tests/static/db_responses/index_mcloud.json"
            ) as handle:
                mcloud_index = json.load(handle)
            # Modified mcloud response. Contains mockable responses CHILD dbs.
            httpx_mock.add_response(
                url=url,
                json=mcloud_index,
            )
        elif provider["id"] == "odbx":
            with open(top_dir / "tests/static/db_responses/index_exmpl.json") as handle:
                # Standard exmpl response. Contains a single CHILD db with `null` base_url
                httpx_mock.add_response(
                    url=url,
                    json=json.load(handle),
                )
    # Mock databases provided by "mcloud" provider (as well as "exmpl", added above)
    mock_gateway_responses(await get_gateway("twodbs"))

    try:
        CONFIG.load_optimade_providers_databases = True

        number_of_databases = await MONGO_DB[
            CONFIG.databases_collection
        ].count_documents({})

        await load_optimade_providers_databases()

        assert (
            "Response from Materials-Consortia's list of OPTIMADE providers was not successful"
            not in caplog.text
        )
        assert (
            "Registering Materials-Consortia list of OPTIMADE providers' databases"
            in caplog.text
        )

        for db in mcloud_index["data"]:
            if db["id"] not in ("2dstructures", "optimade-sample"):
                continue

            assert (
                f"  - {db['attributes']['name']} (id={db['id']!r}) - Checking versioned base URL and /structures"
                in caplog.text
            )
            assert f"  - {db['attributes']['name']} (id={db['id']!r}) - Registered database with id={'mcloud/' + db['id']!r}"

        # No new databases should be added based on the mock responses since ("2dstructures",
        # "optimade-sample") already exist in the collection
        assert (
            await MONGO_DB[CONFIG.databases_collection].count_documents({})
            == number_of_databases
        )
        assert "Created new" not in caplog.text

    finally:
        # Reset CONFIG
        CONFIG.load_optimade_providers_databases = org_val


async def test_bad_provider_databases(
    httpx_mock: "HTTPXMock", caplog: pytest.LogCaptureFixture, generic_meta: dict
):
    """Test load_optimade_providers_databases() for a provider with no announced databases"""
    import re

    import httpx
    from optimade.server.routers.utils import BASE_URL_PREFIXES

    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.events import load_optimade_providers_databases
    from optimade_gateway.mongo.database import MONGO_DB

    def raise_timeout(request: httpx.Request, extensions: dict):
        raise httpx.ReadTimeout(
            f"Unable to read within {extensions['timeout']} seconds", request=request
        )

    no_database_provider = {"data": [], "meta": generic_meta}
    timeout_database_provider = {
        "meta": generic_meta,
        "data": [
            {
                "id": "timeout",
                "attributes": {
                    "base_url": "https://timeout-database",
                    "link_type": "child",
                },
            }
        ],
    }
    bad_response_database_provider = {
        "meta": generic_meta,
        "data": [
            {
                "id": "bad_response",
                "attributes": {
                    "name": "Bad response database",
                    "base_url": {
                        "href": "https://bad-response-database",
                        "meta": {},
                    },
                    "link_type": "child",
                },
            }
        ],
    }

    mock_provider_list = {
        "meta": generic_meta,
        "data": [
            {
                "id": "no_databases",
                "type": "links",
                "attributes": {
                    "name": "No databases provider",
                    "base_url": "https://no-database-provider",
                    "link_type": "external",
                },
            },
            {
                "id": "timeout_db",
                "type": "links",
                "attributes": {
                    "base_url": "https://timeout-database-provider",
                    "link_type": "external",
                },
            },
            {
                "id": "bad_response_db",
                "type": "links",
                "attributes": {
                    "name": "Timeout database provider",
                    "base_url": {
                        "href": "https://bad-response-database-provider",
                        "meta": {},
                    },
                    "link_type": "external",
                },
            },
        ],
    }

    httpx_mock.add_response(
        url=re.compile(r"https://providers\.optimade\.org.*"),
        json=mock_provider_list,
    )
    for index, index_db in enumerate(
        (
            no_database_provider,
            timeout_database_provider,
        )
    ):
        httpx_mock.add_response(
            url=re.compile(
                fr"{mock_provider_list['data'][index]['attributes']['base_url']}.*"
            ),
            json=index_db,
        )
    httpx_mock.add_response(
        url=re.compile(
            fr"{mock_provider_list['data'][-1]['attributes']['base_url']['href']}.*"
        ),
        json=bad_response_database_provider,
    )
    httpx_mock.add_callback(
        callback=raise_timeout,
        url=re.compile(
            fr"{timeout_database_provider['data'][0]['attributes']['base_url']}.*"
        ),
    )
    httpx_mock.add_response(
        url=re.compile(
            fr"{bad_response_database_provider['data'][0]['attributes']['base_url']['href']}.*"
        ),
        status_code=404,
    )

    org_val = CONFIG.load_optimade_providers_databases

    try:
        CONFIG.load_optimade_providers_databases = True

        number_of_databases = await MONGO_DB[
            CONFIG.databases_collection
        ].count_documents({})

        await load_optimade_providers_databases()

        assert (
            "Response from Materials-Consortia's list of OPTIMADE providers was not successful"
            not in caplog.text
        )
        assert (
            "Registering Materials-Consortia list of OPTIMADE providers' databases"
            in caplog.text
        )

        for provider in mock_provider_list["data"]:
            assert (
                f"- {provider['attributes'].get('name', 'N/A')} (id={provider['id']!r}) - Processing"
                in caplog.text
            )

        # No database provider
        assert caplog.text.count("  - No OPTIMADE databases found.") == 1

        # Timeout database
        assert f"  - N/A (id={timeout_database_provider['data'][0]['id']!r}) - Skipping: Timeout while requesting {BASE_URL_PREFIXES['major']}/structures."

        # Bad response database
        assert (
            f"  - {bad_response_database_provider['data'][0]['attributes']['name']} (id={bad_response_database_provider['data'][0]['id']!r}) - Skipping: Response from {BASE_URL_PREFIXES['major']}/structures is not 200 OK."
            in caplog.text
        )

        assert (
            await MONGO_DB[CONFIG.databases_collection].count_documents({})
            == number_of_databases
        )
        assert "Created new" not in caplog.text

    finally:
        # Reset CONFIG
        CONFIG.load_optimade_providers_databases = org_val
