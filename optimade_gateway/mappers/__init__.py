"""OPTIMADE Gateway mappers for entry-endpoint resources.

The design for these mappers is based on the mappers in OPTIMADE Python tools.
"""
from .databases import DatabasesMapper
from .gateways import GatewaysMapper
from .links import LinksMapper
from .queries import QueryMapper

__all__ = ("DatabasesMapper", "GatewaysMapper", "LinksMapper", "QueryMapper")
