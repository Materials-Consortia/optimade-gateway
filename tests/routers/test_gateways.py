import pytest


pytestmark = pytest.mark.asyncio


# @pytest.mark.asyncio
# async def test_get_gateways():
#     """Test GET /gateways"""


async def test_post_gateways(client):
    """Test POST /gateways"""
    from optimade.models import LinksResource
    from optimade_gateway.models.responses import GatewaysResponseSingle

    data = {
        "databases": [
            {
                "id": "test_post_gateways",
                "type": "links",
                "attributes": {
                    "name": "PyTest test_post_gateways",
                    "description": "This is a valid test database",
                    "base_url": "https://example.org/test",
                    "homepage": "https://example.org",
                    "link_type": "child",
                },
            }
        ]
    }

    response = await client("/gateways", method="post", json=data)

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = GatewaysResponseSingle(**response.json())
    assert response

    assert response.meta._optimade_gateway_created, response.meta.dict()

    datum = response.data
    assert datum, response

    for response_db, test_db in zip(datum.attributes.databases, data["databases"]):
        assert (
            response_db.dict() == LinksResource(**test_db).dict()
        ), f"Response: {response_db!r}\n\nTest data: {LinksResource(**test_db)!r}"
