"""Resource mapper for
[`GatewayResource`][optimade_gateway.models.gateways.GatewayResource]."""
from optimade_gateway.mappers.base import BaseResourceMapper
from optimade_gateway.models import GatewayResource


class GatewaysMapper(BaseResourceMapper):
    """[`GatewayResource`][optimade_gateway.models.gateways.GatewayResource] mapper."""

    ENDPOINT = "gateways"
    ENTRY_RESOURCE_CLASS = GatewayResource
