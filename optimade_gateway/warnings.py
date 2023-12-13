"""Server warnings.

The warnings in this module will all be caught by middleware and added to the response
under `meta.warnings`.
"""
from __future__ import annotations

from optimade.server.warnings import OptimadeWarning


class OptimadeGatewayWarning(OptimadeWarning):
    """Base Warning for the `optimade-gateway` package."""


class SortNotSupported(OptimadeGatewayWarning):
    """Sorting (the `sort` query parameter) is currently not supported for gateway
    queries to external OPTIMADE databases. See
    https://optimade.org/optimade-gateway#sorting for more information."""
