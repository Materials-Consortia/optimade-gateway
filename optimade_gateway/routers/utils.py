"""Utility functions for all routers"""
import urllib

from fastapi import Request
from optimade.models import EntryResponseMany, ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import (
    get_base_url,
    handle_response_fields,
    meta_values,
)

from optimade_gateway.mongo.collection import AsyncMongoCollection


async def get_entries(
    collection: AsyncMongoCollection,
    response_cls: EntryResponseMany,
    request: Request,
    params: EntryListingQueryParams,
) -> EntryResponseMany:
    """Generalized /{entries} endpoint getter"""
    results, more_data_available, fields = await collection.find(params=params)

    if more_data_available:
        # Deduce the `next` link from the current request
        query = urllib.parse.parse_qs(request.url.query)
        query["page_offset"] = int(query.get("page_offset", [0])[0]) + len(results)
        urlencoded = urllib.parse.urlencode(query, doseq=True)
        base_url = get_base_url(request.url)

        links = ToplevelLinks(next=f"{base_url}{request.url.path}?{urlencoded}")
    else:
        links = ToplevelLinks(next=None)

    if fields:
        results = handle_response_fields(results, fields)

    return response_cls(
        links=links,
        data=results,
        meta=meta_values(
            url=request.url,
            data_returned=collection.data_returned,
            data_available=collection.data_available,
            more_data_available=more_data_available,
        ),
    )
