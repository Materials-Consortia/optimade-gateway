# Static database responses

This folder contains full responses for various databases to be used for testing.

**Successful responses**:

- `mc2d.json` (https://dev-aiida.materialscloud.org/mc2d/optimade/structures?)
- `optimade-sample.json`(https://dev-aiida.materialscloud.org/optimade-sample/optimade/structures?)
- `providers_optimade.json` (https://providers.optimade.org/v1/links)
  This is an index meta-database, specifically the Materials-Consortia's curated list of OPTIMADE providers, linking to their index meta-databases.
  All providers, except the ones with `base_url=null` have been removed, with the exemption of the `exmpl` provider.
- `index_exmpl.json` (https://providers.optimade.org/index-metadbs/exmpl/v1/links)
  This is an index meta-database, specifically the example index meta-database under the providers.optimade.org domain.
- `index_mcloud.json` (https://dev-www.materialscloud.org/optimade/v1/links)
  This is an index meta-database, specifically the Materials Cloud index meta-database.
  The response has been curated to seem like there are only 6 entries, the only actual databases can be mocked with existing static responses.
- `optimade-sample_single.json` (https://dev-aiida.materialscloud.org/optimade-sample/optimade/structures/1?)

**Errored responses**:

- `mcloud.json` (https://dev-www.materialscloud.org/optimade/structures?filter=elements HAS "Cu"&page_limit=15)
  Response: `404 Not Found`
