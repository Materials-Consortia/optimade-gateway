from typing import Callable, Tuple

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER


async def ci_dev_startup() -> None:
    """Function to run at app startup - only relevant for CI or development to add test data"""
    import os

    if bool(os.getenv("CI", False)):
        LOGGER.info(
            "CI detected - Will load test gateways (after dropping the collection)!"
        )
    elif os.getenv("OPTIMADE_MONGO_DATABASE", "") == "optimade_gateway_dev":
        LOGGER.info(
            "Running in development mode - Will load test gateways (after dropping the collection)!"
        )
    else:
        LOGGER.debug("Not in CI or development mode - will start normally.")
        return

    # Add test gateways
    import json
    from optimade_gateway.mongo.database import MONGO_DB
    from pathlib import Path

    test_data = (
        Path(__file__).parent.parent.joinpath(".ci/test_gateways.json").resolve()
    )

    await MONGO_DB[CONFIG.gateways_collection].drop()

    assert await MONGO_DB[CONFIG.gateways_collection].count_documents({}) == 0

    assert test_data.exists()
    with open(test_data) as handle:
        data = json.load(handle)
    await MONGO_DB[CONFIG.gateways_collection].insert_many(data)


async def load_optimade_providers_databases() -> None:
    """Load in the providers' OPTIMADE databases from Materials-Consortia

    Utilize the Materials-Consortia list of OPTIMADE providers at
    [https://providers.optimade.org](https://providers.optimade.org).
    Load in all databases with a valid base URL.
    """
    import asyncio

    import httpx
    from optimade import __api_version__
    from optimade.models import LinksResponse
    from optimade.models.links import LinkType
    from optimade.server.routers.utils import BASE_URL_PREFIXES

    from optimade_gateway.common.utils import clean_python_types, get_resource_attribute
    from optimade_gateway.models.databases import DatabaseCreate
    from optimade_gateway.queries.perform import db_get_all_resources
    from optimade_gateway.routers.utils import resource_factory

    if not CONFIG.load_optimade_providers_databases:
        LOGGER.debug(
            "Will not load databases from Materials-Consortia list of providers."
        )
        return

    async with httpx.AsyncClient() as client:
        providers = await client.get(
            f"https://providers.optimade.org/v{__api_version__.split('.')[0]}/links"
        )

    if providers.is_error:
        LOGGER.warning(
            "Response from Materials-Consortia's list of OPTIMADE providers was not successful "
            "(status code != 200). No databases will therefore be added at server startup."
        )
        return

    LOGGER.info(
        "Registering Materials-Consortia list of OPTIMADE providers' databases."
    )

    providers = LinksResponse(**providers.json())

    valid_providers = []
    for provider in providers.data:
        if get_resource_attribute(provider, "id") in ("exmpl", "optimade"):
            LOGGER.info(
                "- %s (id=%r) - Skipping: Not a real provider.",
                get_resource_attribute(provider, "attributes.name", "N/A"),
                get_resource_attribute(provider, "id"),
            )
            continue

        if not get_resource_attribute(provider, "attributes.base_url"):
            LOGGER.info(
                "- %s (id=%r) - Skipping: No base URL information.",
                get_resource_attribute(provider, "attributes.name", "N/A"),
                get_resource_attribute(provider, "id"),
            )
            continue

        valid_providers.append(provider)

    # Run queries to each database using the supported major versioned base URL to get a list of
    # the provider's databases.
    # There is no need to use ThreadPoolExecutor here, since we want this to block everything and
    # then finish, before the server actually starts up.
    provider_queries = [
        asyncio.create_task(
            db_get_all_resources(
                database=provider,
                endpoint="links",
                response_model=LinksResponse,
            )
        )
        for provider in valid_providers
    ]

    for query in asyncio.as_completed(provider_queries):
        provider_databases, provider = await query

        LOGGER.info(
            "- %s (id=%r) - Processing",
            get_resource_attribute(provider, "attributes.name", "N/A"),
            get_resource_attribute(provider, "id"),
        )
        if not provider_databases:
            LOGGER.info("  - No OPTIMADE databases found.")
            continue

        provider_databases = [
            db
            for db in provider_databases
            if await clean_python_types(
                get_resource_attribute(db, "attributes.link_type", "")
            )
            == LinkType.CHILD.value
        ]

        if not provider_databases:
            LOGGER.info("  - No OPTIMADE databases found.")
            continue

        for database in provider_databases:
            if not get_resource_attribute(database, "attributes.base_url"):
                LOGGER.info(
                    "  - %s (id=%r) - Skipping: No base URL information.",
                    get_resource_attribute(database, "attributes.name", "N/A"),
                    get_resource_attribute(database, "id"),
                )
                continue

            LOGGER.info(
                "  - %s (id=%r) - Checking versioned base URL and /structures",
                get_resource_attribute(database, "attributes.name", "N/A"),
                get_resource_attribute(database, "id"),
            )

            async with httpx.AsyncClient() as client:
                try:
                    db_response = await client.get(
                        f"{str(get_resource_attribute(database, 'attributes.base_url')).rstrip('/')}{BASE_URL_PREFIXES['major']}/structures",
                    )
                except httpx.ReadTimeout:
                    LOGGER.info(
                        "  - %s (id=%r) - Skipping: Timeout while requesting %s/structures.",
                        get_resource_attribute(database, "attributes.name", "N/A"),
                        get_resource_attribute(database, "id"),
                        BASE_URL_PREFIXES["major"],
                    )
                    continue
            if db_response.status_code != 200:
                LOGGER.info(
                    "  - %s (id=%r) - Skipping: Response from %s/structures is not 200 OK.",
                    get_resource_attribute(database, "attributes.name", "N/A"),
                    get_resource_attribute(database, "id"),
                    BASE_URL_PREFIXES["major"],
                )
                continue

            new_id = (
                f"{get_resource_attribute(provider, 'id')}/{get_resource_attribute(database, 'id')}"
                if len(provider_databases) > 1
                else get_resource_attribute(database, "id")
            )
            registered_database, _ = await resource_factory(
                DatabaseCreate(
                    id=new_id,
                    **await clean_python_types(
                        get_resource_attribute(database, "attributes", {})
                    ),
                )
            )
            LOGGER.info(
                "  - %s (id=%r) - Registered database with id=%r",
                get_resource_attribute(database, "attributes.name", "N/A"),
                get_resource_attribute(database, "id"),
                registered_database.id,
            )


EVENTS: Tuple[Tuple[str, Callable[[], None]]] = (
    ("startup", ci_dev_startup),
    ("startup", load_optimade_providers_databases),
)
"""A tuple of all pairs of events and event functions.

To use this tuple of tuples:

```python
from fastapi import FastAPI
APP = FastAPI()
for event, func in EVENTS:
    APP.add_event_handler(event, func)
```

"""
