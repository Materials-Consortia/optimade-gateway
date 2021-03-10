"""Tests for /gateways/{gateway_id}/versions endpoint"""
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_versions(client):
    """Test GET /versions"""
    from optimade import __api_version__

    response = await client("/versions")

    assert response.status_code == 200, f"Request failed: {response.text}"

    assert response.text == f"version\n{__api_version__.split('.')[0]}"
    assert "content-type" in response.headers, response.headers
    for media_type_content in ("text/csv", "header=present"):
        assert media_type_content in response.headers.get("content-type", "")
