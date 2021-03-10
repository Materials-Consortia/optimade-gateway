"""Tests for /links endpoint"""
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_links(client):
    """Test GET /links"""
    from optimade.models import LinksResponse

    response = await client("/links")

    assert response.status_code == 200, f"Request failed: {response.json()}"
    response = LinksResponse(**response.json())
    assert response

    assert response.meta.data_returned == 2
    assert response.meta.data_available == 2
    assert not response.meta.more_data_available
