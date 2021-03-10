"""Tests for /versions endpoint

As this is not implemented in the current package, but rather used directly from the `optimade`
package, we just check it exists and returns the response we would expect.
"""
import pytest


pytestmark = pytest.mark.asyncio


async def test_get_versions(client):
    """Test GET /versions"""
    from httpx import Response
    from optimade import __api_version__

    response: Response = await client("/versions")

    assert response.status_code == 200, f"Request failed: {response.text}"

    assert response.text == f"version\n{__api_version__.split('.')[0]}"
    assert "content-type" in response.headers, response.headers
    for media_type_content in ("text/csv", "header=present"):
        assert media_type_content in response.headers.get("content-type", "")
