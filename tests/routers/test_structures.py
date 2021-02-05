"""Tests for /gateways/{gateway_id}/structures endpoints"""
# pylint: disable=import-error,no-name-in-module
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_gateways(client, get_gateway):
    """Test GET /gateways/{gateway_id}/structures"""
    from optimade.models import StructureResponseMany  # , StructureResource
    from optimade.server.config import CONFIG
    import requests

    gateway_id = "twodbs"

    response = await client(f"/gateways/{gateway_id}/structures")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = StructureResponseMany(**response.json())
    assert response

    assert response.meta.more_data_available

    more_data_available = False
    data_returned = 0
    data_available = 0
    data = []

    gateway = await get_gateway(gateway_id)
    for database in gateway["databases"]:
        url = f"{database['attributes']['base_url']}/structures?page_limit={CONFIG.page_limit}"
        db_response = requests.get(url)
        assert (
            db_response.status_code == 200
        ), f"Request to {url} failed: {db_response.json()}"
        db_response = db_response.json()

        data_returned += db_response["meta"]["data_returned"]
        data_available += db_response["meta"]["data_available"]
        if not more_data_available:
            more_data_available = db_response["meta"]["more_data_available"]

        for datum in db_response["data"]:
            datum["id"] = f"{database['id']}/{datum['id']}"
            data.append(datum)

    assert data_returned == response.meta.data_returned
    assert data_available == response.meta.data_available
    assert more_data_available == response.meta.more_data_available

    data = sorted(data, key=lambda datum: "/".join(datum["id"].split("/")[1:]))
    # TODO: Uncomment when aiidateam/aiida-optimade#197 has been fixed (https://github.com/aiidateam/aiida-optimade/issues/197).
    # assert [StructureResource(**_).dict() for _ in data] == [_.dict() for _ in response.data]
