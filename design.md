# Design of the OPTIMADE gateway

The OPTIMADE gateway is intended to be implemented into the MarketPlace platform.
Therefore, it should implement the MarketPlace Data Source API, as well as endpoints needed for the gateway capabilities themselves.
To this end, the following sections defines/recaps these APIs and capabilities.

## MarketPlace Data Source API

The MarketPlace Data Source API developed in T2.2 of the MarketPlace project.  
It can be found on the Fraunhofer GitLab [here](https://gitlab.cc-asp.fraunhofer.de/MarketPlace/grantadatasourceapi).

Outline of the currently defined endpoints.
Note, if there is no HTTP method next to the endpoint, it is not an available and reachable endpoint.

`/marketplace/`

- `/schemas/` (`GET`)

  - `/{schema_id}/`

    - `/attributes` (`GET`)
    - `/export` (`POST`)
    - `/search` (`POST`)

## OPTIMADE gateway API

The suggested OPTIMADE gateway API.

This API is based on the expected capabilities [outlined below](#OPTIMADE-gateway-capabilities).

`/optimade/`  
**Methods**: `GET`  
**Behavior**: Introspective/static metadata overview of server.

- `/search/`  
  **Methods**: `POST` **or** `GET`  
  **Behavior**: Orchestrate a search.

- `/gateways/`  
  **Methods**: `GET`  
  **Behavior**:  
  _Standard reponse_: Introspective/static metadata overview of all gateways.  
  _Using special query parameter_: Create/retrieve and return unique gateway ID.

  - `/{gateway_id}/`  
    **Methods**: `POST` **or** `GET`  
    **Behavior**: Create/retrieve search ID and return unique search ID.
    Start asynchronous search task.

    Either:

    - `/searches/`  
      **Methods**: None  
      **Behavior**: Disallowed.  
      _Note_: This endpoint could support `GET` requests with similar functionality and behavior as for `/gateways/`?
      This would move some functionality away from `/{gateway_id}/` to this endpoint.
      Making `/{gateway_id}/` act as a mix of `/search/` and `/gateways/` in terms of orchestrating the search and returning introspective/static metadata about the gateway.

      - `/{search_id}/`  
        **Methods**: `GET`  
        **Behavior**: Return current results according to state of asynchronous search task.

    or:

    - `/{search_id}/`  
        **Methods**: `GET`  
        **Behavior**: Return current results according to state of asynchronous search task.

## OPTIMADE gateway capabilities

- [Searching in multiple OPTIMADE databases](#Searching).
- [Utilize the OPTIMADE filter language](#OPTIMADE-filter-language).
- [Retrieve entries (OPTIMADE structures) as JSON-serialized CUDS](#Retrieval-formats).

### Design ideas and comments by Simon Adorf ([@csadorf](https://github.com/csadorf))

I think the way you would achieve the “selection” of databases is by creating provider-specific endpoints like this:

```console
GET
/gateway?providers=abc,def,xyz
```

This will return a deterministic gateway id related to specific set of providers, which you will then use for further queries like this:

```console
GET
/gateway/{gateway_id}/structures/
```

etc.

The gateway id would provide introspection, so `/gateway/{gateway_id}` returns some information about the gateway (supported OPTIMADE API, list of providers) etc.  
You would cache the gateway id in the client, so you don’t have to make two requests for each query.  
If you don’t provide a list of providers, the current default set is used.
But this ensures that the REST API is actually stateless, because one gateway is always tied to a specific set of providers even if the default list is changed.
Obviously, if you use a gateway that includes providers that are no longer available you would respond with code 503 or so.

This design solves the issue of how to provide a gateway that implements the OPTIMADE API and allows for the selection of providers.  
I assume your results are paginated, so IMO — unless you request a specific order — you should just return results as they come in.
You need to implement this gateway asynchronously anyways so it really does not matter whether you include slow providers or not.

Of course, this changes if the user requests a specific order, but that’s just how it is.
From a user perspective it would make sense to me that such a query across multiple providers may take a while.

You should definitely define a timeout for each gateway where if a provider does not respond by then, the result is returned regardless of whether the provider has responded.
Or you respond with a time out code.

### Searching

Taking Simon's comments into account, the search capability should be:

- Asynchronous; and
- Dynamic.

The asynchronicity comes from creating web calls (possibly using CORS) to each (chosen) database asynchronously, collating the results in a single (gateway) endpoint.

The dynamics here relate to the suggested dynamic creation (and possible deletion) of gateway IDs under a `/gateway`-endpoint.

#### GET requests

Essentially, for each search, a new gateway will be created (if needed) with a unique ID.
This unique ID will constitue the content of the initial response after performing a search, so that the user can go to the new gateway ID-specific endpoint to retrieve the results.
To make this easier for the user, the server could automatically redirect the user after creating the endpoint.
Here the response will contain the currently retrieved results as well as som metadata information about how the search is going and a general overview.

This would ideally result in the following search sequence:

![Search sequence](searching_get.svg)

The final `GET` request can be repeated to retrieve more results during the timeline of the search happening, and to retrieve the final list of results in a set time period after the search has finished.

#### POST requests

One could also think of using `POST` requests instead, containing the OPTIMADE query parameters alongside with other information, mainly utilized for the `/gateway/{unique ID}`-endpoints.
The response could contain a link or simply redirect to a `/gateway/{unique ID}/{search unique ID}`-endpoint.
The latter part could also be done for the `GET` approach, since a specific gateway should support multiple unique simultaneous searched.
Since the searches are asynchronous, the results don't come back from all resources simultaneously, thus demanding an extra endpoint, where the continuously updating results can be found - as well as the final list of results for a specific search.

This differs from the section above, where a `GET` request should contain query parameters in the URL and this will be correlated with an ongoing (unique) search in the backend, which would potentially allow different users to experience the same loading of results if they performed the same search in the same gateway, even at slightly different times during the searching period.

A sequence would ideally look this:

![Search sequence](searching_post.svg)

#### Conclusion

The best approach here would be to create unique search IDs under each unique gateway, pertaining to a specific search.  
In the same way that gateways may be reused, search results may be reused.
However, to ensure the "freshness" of the data, the "live"-period for any unique search should be significantly smaller than that of any unique gateway.

`POST` requests may be preferred due to the ability of combining OPTIMADE-specific query data and gateway-specific data.

**Suggested search sequence diagram**:

![Search sequence](searching.svg)

### OPTIMADE filter language

The filter language will be reused as the filter language for any search in any gateway.

The filter language is defined in [the OPTIMADE specification](https://github.com/Materials-Consortia/OPTIMADE/blob/develop/optimade.rst#api-filtering-format-specification).

### Retrieval formats

All responses will be in JSON (for now).

To choose the retrieval format of the structure, a query parameter will be dedicated for the `/{search unique ID}` endpoint.

#### OPTIMADE

The standard OPTIMADE format for defining structures will be reused for listing the structure entries.

See [the OPTIMADE specification](https://github.com/Materials-Consortia/OPTIMADE/blob/develop/optimade.rst#structures-entries) for a list of properties defining the structures entry.

When returning the results in this format, the whole response should be compliant with a standard OPTIMADE response as is expected in the `/structures`-endpoint.

#### CUDS

Utilizing the `optimade2cuds` Python package in the [SimOPTIMADE](https://gitlab.cc-asp.fraunhofer.de/MarketPlace/SimOPTIMADE) repository on the Fraunhofer GitLab for the MarketPlace project, the resulting OPTIMADE structure can be converted to Python CUDS objects.
From there they can be serialized to JSON representations (using the [OSP-Core](https://github.com/simphony/osp-core) package) and returned as a search result response.
