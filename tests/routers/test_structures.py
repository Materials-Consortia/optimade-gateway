"""Tests for /gateways/{gateway_id}/structures endpoints"""
# pylint: disable=import-error,no-name-in-module
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_structures(client, get_gateway):
    """Test GET /gateways/{gateway_id}/structures"""
    from optimade.models import StructureResponseMany, StructureResource
    from optimade_gateway.common.config import CONFIG
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

    assert len(response.data) == CONFIG.page_limit * len(gateway["databases"])

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

    data.sort(key=lambda datum: datum["id"])
    data.sort(key=lambda datum: "/".join(datum["id"].split("/")[1:]))
    assert [StructureResource(**_).dict() for _ in data] == [
        _.dict() for _ in response.data
    ], (
        f"IDs in test not in response: {set([_['id'] for _ in data]) - set([_.id for _ in response.data])}\n\n"
        f"IDs in response not in test: {set([_.id for _ in response.data]) - set([_['id'] for _ in data])}\n\n"
    )


async def test_get_single_structure(client, get_gateway):
    """TEST GET /gateways/{gateway_id}/structures/{structure_id}"""
    from optimade.models import StructureResponseOne, StructureResource
    import requests

    gateway_id = "singledb"
    structure_id = "optimade-sample/1"

    response = await client(f"/gateways/{gateway_id}/structures/{structure_id}")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = StructureResponseOne(**response.json())
    assert response

    assert not response.meta.more_data_available

    gateway = await get_gateway(gateway_id)
    database = gateway["databases"][0]

    assert response.data is not None

    url = f"{database['attributes']['base_url']}/structures/{structure_id[len(database['id']) + 1:]}"
    db_response = requests.get(url)
    assert (
        db_response.status_code == 200
    ), f"Request to {url} failed: {db_response.json()}"
    db_response = db_response.json()

    assert db_response["data"] is not None
    db_response["data"]["id"] = f"{database['id']}/{db_response['data']['id']}"

    assert db_response["meta"]["data_returned"] == response.meta.data_returned
    assert response.meta.data_available is None
    assert (
        db_response["meta"]["more_data_available"] == response.meta.more_data_available
    )

    assert StructureResource(**db_response["data"]).dict() == response.data.dict()
