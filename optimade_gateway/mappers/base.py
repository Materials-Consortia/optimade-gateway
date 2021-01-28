from optimade.server.mappers.entries import (
    BaseResourceMapper as OptimadeBaseResourceMapper,
)

__all__ = ("BaseResourceMapper",)


class BaseResourceMapper(OptimadeBaseResourceMapper):

    ALIASES = (("id", "_id"),)
