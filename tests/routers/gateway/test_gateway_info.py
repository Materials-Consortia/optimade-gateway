"""Tests for /gateways/{gateway_id}/info endpoint"""
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_gateway_info(client, get_gateway):
    """Test GET /gateways/{gateway_id}/info"""
    from optimade.models import InfoResponse

    from optimade_gateway.common.config import CONFIG

    available_endpoints = sorted(["info", "links", "structures"])
    entry_types_by_format = {"json": ["structures"]}

    gateway_id = "twodbs"

    response = await client(f"/gateways/{gateway_id}/info")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = InfoResponse(**response.json())
    assert response

    assert response.meta.data_returned == 1
    assert response.meta.data_available == 1
    assert not response.meta.more_data_available
    assert response.data.attributes.available_endpoints == available_endpoints
    assert response.data.attributes.entry_types_by_format == entry_types_by_format
    assert (
        not response.data.attributes.is_index
        or response.data.attributes.is_index is None
    )

    gateway = await get_gateway(gateway_id)

    assert getattr(response.meta, f"_{CONFIG.provider.prefix}_gateway", {}) == {
        "databases": [
            {"id": _.get("id", "NOT FOUND"), "type": _.get("type", "NOT FOUND")}
            for _ in gateway.get("databases", [])
        ]
    }


async def test_get_versioned_gateway_info(client, get_gateway):
    """Test GET /gateways/{gateway_id}/{version}/info"""
    from optimade.models import InfoResponse
    from optimade.server.routers.utils import BASE_URL_PREFIXES

    from optimade_gateway.common.config import CONFIG

    available_endpoints = sorted(["info", "links", "structures"])
    entry_types_by_format = {"json": ["structures"]}

    gateway_id = "twodbs"

    for version in BASE_URL_PREFIXES.values():
        response = await client(f"/gateways/{gateway_id}{version}/info")

        assert response.status_code == 200, f"Request failed: {response.json()}"
        response = InfoResponse(**response.json())
        assert response

        assert response.meta.data_returned == 1
        assert response.meta.data_available == 1
        assert not response.meta.more_data_available
        assert response.data.attributes.available_endpoints == available_endpoints
        assert response.data.attributes.entry_types_by_format == entry_types_by_format
        assert (
            not response.data.attributes.is_index
            or response.data.attributes.is_index is None
        )

        gateway = await get_gateway(gateway_id)

        assert getattr(response.meta, f"_{CONFIG.provider.prefix}_gateway", {}) == {
            "databases": [
                {"id": _.get("id", "NOT FOUND"), "type": _.get("type", "NOT FOUND")}
                for _ in gateway.get("databases", [])
            ]
        }


async def test_bad_versioned_gateway_info(client):
    """Test GET /gateways/{gateway_id}/{version}/info with wrong version"""
    from optimade.models import ErrorResponse, OptimadeError
    from optimade.server.exceptions import VersionNotSupported
    from optimade.server.routers.utils import BASE_URL_PREFIXES

    gateway_id = "twodbs"

    wrong_versions = [
        (
            # Correct syntax - unsupport version
            "v0.1.0",
            {
                "detail": (
                    "version v0.1.0 is not supported. Supported versions: "
                    f"{[_[1:] for _ in BASE_URL_PREFIXES.values()]}"
                ),
                "title": "Version Not Supported",
                "status": "553",
            },
        ),
        (
            # Incorrect syntax - supported version
            BASE_URL_PREFIXES["patch"][len("/v") :],
            {
                "detail": f"version MUST be one of {[_[1:] for _ in BASE_URL_PREFIXES.values()]}",
                "title": "Not Found",
                "status": "404",
            },
        ),
    ]

    for version, error_data in wrong_versions:
        error_resource = OptimadeError(**error_data)

        if version == "v0.1.0":
            with pytest.raises(
                VersionNotSupported,
                match=fr"The parsed versioned base URL '/{version}.*",
            ):
                response = await client(f"/gateways/{gateway_id}/{version}/info")
            return
        else:
            response = await client(f"/gateways/{gateway_id}/{version}/info")

        assert response.status_code == int(
            error_resource.status
        ), f"Request succeeded, where it should've failed: {response.json()}"
        response = ErrorResponse(**response.json())
        assert response

        assert response.meta.data_returned == 0
        assert response.meta.data_available == 0
        assert not response.meta.more_data_available

        assert len(response.errors) == 1
        assert response.errors == [error_resource]


async def test_get_gateway_info_entry(client):
    """Test GET /gateways/{gateway_id}/info/{entry}"""
    from optimade.models import EntryInfoResponse

    from optimade_gateway.routers.gateway.info import ENTRY_INFO_SCHEMAS

    gateway_id = "singledb"

    for entry_endpoint in ENTRY_INFO_SCHEMAS:
        response = await client(f"/gateways/{gateway_id}/info/{entry_endpoint}")

        assert response.status_code == 200, f"Request failed: {response.json()}"
        response = EntryInfoResponse(**response.json())
        assert response

        assert response.meta.data_returned == 1
        assert response.meta.data_available == 1
        assert not response.meta.more_data_available


async def test_get_versioned_gateway_info_entry(client, get_gateway):
    """Test GET /gateways/{gateway_id}/{version}/info/{entry}"""
    from optimade.models import EntryInfoResponse
    from optimade.server.routers.utils import BASE_URL_PREFIXES

    from optimade_gateway.routers.gateway.info import ENTRY_INFO_SCHEMAS

    gateway_id = "singledb"

    for version in BASE_URL_PREFIXES.values():
        for entry_endpoint in ENTRY_INFO_SCHEMAS:
            response = await client(
                f"/gateways/{gateway_id}{version}/info/{entry_endpoint}"
            )

            assert response.status_code == 200, f"Request failed: {response.json()}"
            response = EntryInfoResponse(**response.json())
            assert response

            assert response.meta.data_returned == 1
            assert response.meta.data_available == 1
            assert not response.meta.more_data_available


async def test_bad_versioned_gateway_info_entry(client):
    """Test GET /gateways/{gateway_id}/{version}/info/{entry} with wrong version"""
    from optimade.models import ErrorResponse, OptimadeError
    from optimade.server.exceptions import VersionNotSupported
    from optimade.server.routers.utils import BASE_URL_PREFIXES

    from optimade_gateway.routers.gateway.info import ENTRY_INFO_SCHEMAS

    gateway_id = "singledb"

    wrong_versions = [
        (
            # Correct syntax - unsupport version
            "v0.1.0",
            {
                "detail": (
                    "version v0.1.0 is not supported. Supported versions: "
                    f"{[_[1:] for _ in BASE_URL_PREFIXES.values()]}"
                ),
                "title": "Version Not Supported",
                "status": "553",
            },
        ),
        (
            # Incorrect syntax - supported version
            BASE_URL_PREFIXES["patch"][len("/v") :],
            {
                "detail": f"version MUST be one of {[_[1:] for _ in BASE_URL_PREFIXES.values()]}",
                "title": "Not Found",
                "status": "404",
            },
        ),
    ]

    for version, error_data in wrong_versions:
        error_resource = OptimadeError(**error_data)

        for entry_endpoint in ENTRY_INFO_SCHEMAS:
            if version == "v0.1.0":
                with pytest.raises(
                    VersionNotSupported,
                    match=fr"The parsed versioned base URL '/{version}.*",
                ):
                    response = await client(
                        f"/gateways/{gateway_id}/{version}/info/{entry_endpoint}"
                    )
                return
            else:
                response = await client(
                    f"/gateways/{gateway_id}/{version}/info/{entry_endpoint}"
                )

            assert response.status_code == int(
                error_resource.status
            ), f"Request succeeded, where it should've failed: {response.json()}"
            response = ErrorResponse(**response.json())
            assert response

            assert response.meta.data_returned == 0
            assert response.meta.data_available == 0
            assert not response.meta.more_data_available

            assert len(response.errors) == 1
            assert response.errors == [error_resource]
