# OPTIMADE Gateway

[![codecov](https://codecov.io/gh/Materials-Consortia/optimade-gateway/branch/main/graph/badge.svg?token=94aa7IhlUD)](https://codecov.io/gh/Materials-Consortia/optimade-gateway) [![CI Status](https://github.com/Materials-Consortia/optimade-gateway/actions/workflows/ci_tests.yml/badge.svg?branch=main)](https://github.com/Materials-Consortia/optimade-gateway/actions?query=branch%3Amain) [![Last Commit](https://img.shields.io/github/last-commit/Materials-Consortia/optimade-gateway/main?logo=github)](https://github.com/Materials-Consortia/optimade-gateway/pulse)

A REST API server acting as a gateway for databases with an OPTIMADE API, handling the distribution and collection of a single query to several different OPTIMADE databases.

The design outline is available [here](design.md).

## Known limitations

Here follows a list of known limitations and oddities of the current OPTIMADE gateway code.

### Pagination

Pagination is a bit awkward in its current implementation state.

When using the `page_limit` query parameter for a gateway query for gateways with multiple databases, i.e., for `GET /gateways/{gateway ID}/structures` and `GET /queries/{query ID}`, the resulting entry-resource number is the product of the `page_limit` value and the number of databases in the gateway (maximum).
This is because the `page_limit` query parameter is passed straight through to the external database requests, and the returned entries are stitched together for the gateway response.

So effectively, when querying `GET /gateways/{gateway with N databases}/structures?page_limit=5` the resulting (maximum) number of entries returned in the response (the size of the `data` array in the response) will be N x 5, and not 5 as would otherwise be expected.

The intention is to fix this in the future, either through short-time caching of external database responses, or figuring out if there is a usable algorithm that doesn't extend the number of external requests (and therefore the gateway response times) by too much.

### Sorting

Sorting is supported for all the gateway's own resources, i.e., in the `/gateways`, `/databases`, and `/queries` endpoints.
But sorting is **not supported** for the results from external OPTIMADE databases.
This means the `sort` query parameter has no effect in the `GET /gateways/{gateway ID}/structures` and `GET /queries/{query ID}` endpoints.

This shortcoming is a direct result of the current `page_limit` query parameter handling, and the [limitation of the same](#pagination).

## License, copyright & funding support

All code in this repository was originally written by Casper Welzel Andersen ([@CasperWA](https://github.com/CasperWA)).
The design for the gateway as outlined in [design.md](design.md) was a joint effort between Casper Welzel Andersen & Carl Simon Adorf ([@csadorf](https://github.com/csadorf)).

All files in this repository are licensed under the [MIT license](LICENSE.md) with copyright &copy; 2021 Casper Welzel Andersen & THEOS, EPFL.

### Funding support

This work was funded by [THEOS](http://theossrv1.epfl.ch), [EPFL](https://epfl.ch) and [the MarketPlace project](https://www.the-marketplace-project.eu/).

The MarketPlace project is funded by [Horizon 2020](https://ec.europa.eu/programmes/horizon2020/) under H2020-NMBP-25-2017 call with Grant agreement number: 760173.

<div style="text-align:center">
<img src="images/THEOS_logo.png" alt="THEOS" width="73" style="margin:0px 12px"/><img src="images/EPFL_Logo_184X53.svg" alt="EPFL" width="120" style="margin:0px 12px"/><img src="images/MARKETPLACE_LOGO_300dpi.png" alt="The MarketPlace Project" width="159" style="margin:0px 12px"/>
</div>
