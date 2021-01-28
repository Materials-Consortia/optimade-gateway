from optimade_gateway.mappers.base import BaseResourceMapper

__all__ = ("GatewaysMapper",)


class GatewaysMapper(BaseResourceMapper):

    ENDPOINT = "gateways"
