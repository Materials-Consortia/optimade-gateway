import re
from typing import TYPE_CHECKING

from optimade.server.exceptions import VersionNotSupported
from optimade.server.routers.utils import BASE_URL_PREFIXES, get_base_url
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import Request
    from starlette.datastructures import URL


class CheckWronglyVersionedBaseUrlsGateways(BaseHTTPMiddleware):
    """If a non-supported versioned base URL is supplied to a gateway
    return `553 Version Not Supported`."""

    @staticmethod
    async def check_url(url: "URL"):
        """Check URL path for versioned part.

        Parameters:
            url: A complete `urllib`-parsed raw URL.

        Raises:
            VersionNotSupported: If the URL represents an OPTIMADE versioned base URL
                and the version part is not supported by the implementation.

        """
        base_url = get_base_url(url)
        optimade_path = f"{url.scheme}://{url.netloc}{url.path}"[len(base_url) :]
        match = re.match(
            r"^/gateways/[^/\s]+(?P<version>/v[0-9]+(\.[0-9]+){0,2}).*", optimade_path
        )
        if match is not None:
            if match.group("version") not in BASE_URL_PREFIXES.values():
                raise VersionNotSupported(
                    detail=(
                        f"The parsed versioned base URL {match.group('version')!r} from "
                        f"{url} is not supported by this implementation. "
                        f"Supported versioned base URLs are: {', '.join(BASE_URL_PREFIXES.values())}"
                    )
                )

    async def dispatch(self, request: "Request", call_next):
        if request.url.path:
            await self.check_url(request.url)
        response = await call_next(request)
        return response
