"""
Pydantic models

All pydantic data and response models used to define the API can be found in this
module.
"""

from __future__ import annotations

from .databases import DatabaseCreate
from .gateways import GatewayCreate, GatewayResource, GatewayResourceAttributes
from .queries import (
    EndpointEntryType,
    GatewayQueryResponse,
    QueryCreate,
    QueryResource,
    QueryState,
)
from .resources import EntryResourceCreate
from .responses import (
    DatabasesResponse,
    DatabasesResponseSingle,
    GatewaysResponse,
    GatewaysResponseSingle,
    QueriesResponse,
    QueriesResponseSingle,
)
from .search import Search

__all__ = (
    "DatabaseCreate",
    "DatabasesResponse",
    "DatabasesResponseSingle",
    "EndpointEntryType",
    "EntryResourceCreate",
    "GatewayCreate",
    "GatewayQueryResponse",
    "GatewayResource",
    "GatewayResourceAttributes",
    "GatewaysResponse",
    "GatewaysResponseSingle",
    "QueriesResponse",
    "QueriesResponseSingle",
    "QueryCreate",
    "QueryResource",
    "QueryState",
    "Search",
)
