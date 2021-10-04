# Changelog

## [v0.2.1](https://github.com/Materials-Consortia/optimade-gateway/tree/v0.2.1) (2021-10-04)

[Full Changelog](https://github.com/Materials-Consortia/optimade-gateway/compare/v0.2.0...v0.2.1)

**Implemented enhancements:**

- Run keep-up-to-date workflow immediately with push [\#140](https://github.com/Materials-Consortia/optimade-gateway/issues/140)
- Update to versioned documentation [\#132](https://github.com/Materials-Consortia/optimade-gateway/issues/132)
- Use `bandit`, `pylint`, `safety`, and `mypy` [\#119](https://github.com/Materials-Consortia/optimade-gateway/pull/119) ([CasperWA](https://github.com/CasperWA))

**Fixed bugs:**

- GH Release action overwrites release description [\#155](https://github.com/Materials-Consortia/optimade-gateway/issues/155)
- Fix condition in `main` docs deployment [\#152](https://github.com/Materials-Consortia/optimade-gateway/issues/152)
- Properly authenticate the use of `gh api` in workflow [\#150](https://github.com/Materials-Consortia/optimade-gateway/issues/150)
- Double documentation deploy during release [\#145](https://github.com/Materials-Consortia/optimade-gateway/issues/145)
- Allow beta/alpha releases [\#143](https://github.com/Materials-Consortia/optimade-gateway/issues/143)
- Use protected-push action for keep-up-to-date workflow [\#138](https://github.com/Materials-Consortia/optimade-gateway/issues/138)
- Workflow not working [\#133](https://github.com/Materials-Consortia/optimade-gateway/issues/133)
- Attempt with fetch-depth 0 [\#154](https://github.com/Materials-Consortia/optimade-gateway/pull/154) ([CasperWA](https://github.com/CasperWA))
- Set git config before `mike deploy` [\#144](https://github.com/Materials-Consortia/optimade-gateway/pull/144) ([CasperWA](https://github.com/CasperWA))
- Use `git push` instead of action [\#136](https://github.com/Materials-Consortia/optimade-gateway/pull/136) ([CasperWA](https://github.com/CasperWA))

**Closed issues:**

- Update cron timings for dependency workflows [\#147](https://github.com/Materials-Consortia/optimade-gateway/issues/147)
- Use `gh-pages` in documentation deploy workflows [\#142](https://github.com/Materials-Consortia/optimade-gateway/issues/142)

**Merged pull requests:**

- Update dependencies [\#159](https://github.com/Materials-Consortia/optimade-gateway/pull/159) ([CasperWA](https://github.com/CasperWA))
- Deploy docs to `gh-pages` branch [\#157](https://github.com/Materials-Consortia/optimade-gateway/pull/157) ([CasperWA](https://github.com/CasperWA))
- Use GH CLI instead of release action [\#156](https://github.com/Materials-Consortia/optimade-gateway/pull/156) ([CasperWA](https://github.com/CasperWA))
- Fix conditional docs `main` build [\#153](https://github.com/Materials-Consortia/optimade-gateway/pull/153) ([CasperWA](https://github.com/CasperWA))
- Add GITHUB\_TOKEN env var to authenticate gh CLI [\#151](https://github.com/Materials-Consortia/optimade-gateway/pull/151) ([CasperWA](https://github.com/CasperWA))
- Fix double docs deployment on release [\#149](https://github.com/Materials-Consortia/optimade-gateway/pull/149) ([CasperWA](https://github.com/CasperWA))
- Update cron times [\#148](https://github.com/Materials-Consortia/optimade-gateway/pull/148) ([CasperWA](https://github.com/CasperWA))
- Update dependencies [\#146](https://github.com/Materials-Consortia/optimade-gateway/pull/146) ([CasperWA](https://github.com/CasperWA))
- Run up-to-date workflow immediately upon push [\#141](https://github.com/Materials-Consortia/optimade-gateway/pull/141) ([CasperWA](https://github.com/CasperWA))
- Push via CasperWA/push-protected action [\#139](https://github.com/Materials-Consortia/optimade-gateway/pull/139) ([CasperWA](https://github.com/CasperWA))
- Use versioned documentation [\#137](https://github.com/Materials-Consortia/optimade-gateway/pull/137) ([CasperWA](https://github.com/CasperWA))
- Fetch everything and ensure correct checkout [\#135](https://github.com/Materials-Consortia/optimade-gateway/pull/135) ([CasperWA](https://github.com/CasperWA))
- Attempt to fix workflow [\#134](https://github.com/Materials-Consortia/optimade-gateway/pull/134) ([CasperWA](https://github.com/CasperWA))
- Run dependabot workflow more often [\#130](https://github.com/Materials-Consortia/optimade-gateway/pull/130) ([CasperWA](https://github.com/CasperWA))
- Only update permanent dependabot branch after CI [\#127](https://github.com/Materials-Consortia/optimade-gateway/pull/127) ([CasperWA](https://github.com/CasperWA))
- Don't use `env` outside of usable scope [\#126](https://github.com/Materials-Consortia/optimade-gateway/pull/126) ([CasperWA](https://github.com/CasperWA))
- Setup dependabot automation [\#125](https://github.com/Materials-Consortia/optimade-gateway/pull/125) ([CasperWA](https://github.com/CasperWA))
- Don't load providers on startup by default [\#121](https://github.com/Materials-Consortia/optimade-gateway/pull/121) ([CasperWA](https://github.com/CasperWA))
- Update pylint requirement from ~=2.10 to ~=2.11 [\#120](https://github.com/Materials-Consortia/optimade-gateway/pull/120) ([dependabot[bot]](https://github.com/apps/dependabot))

## [v0.2.0](https://github.com/Materials-Consortia/optimade-gateway/tree/v0.2.0) (2021-09-07)

[Full Changelog](https://github.com/Materials-Consortia/optimade-gateway/compare/v0.1.2...v0.2.0)

**Implemented enhancements:**

- Minor re-design [\#82](https://github.com/Materials-Consortia/optimade-gateway/pull/82) ([CasperWA](https://github.com/CasperWA))

**Fixed bugs:**

- Fix CD - remnants from \#82 [\#117](https://github.com/Materials-Consortia/optimade-gateway/issues/117)

**Merged pull requests:**

- Remove references to docker\_config.json [\#118](https://github.com/Materials-Consortia/optimade-gateway/pull/118) ([CasperWA](https://github.com/CasperWA))
- Return to major version tags \(where available\) for GH Actions [\#114](https://github.com/Materials-Consortia/optimade-gateway/pull/114) ([CasperWA](https://github.com/CasperWA))
- Update dependencies [\#112](https://github.com/Materials-Consortia/optimade-gateway/pull/112) ([CasperWA](https://github.com/CasperWA))
- Update pytest-httpx requirement from ~=0.12.0 to ~=0.12.1 [\#108](https://github.com/Materials-Consortia/optimade-gateway/pull/108) ([dependabot[bot]](https://github.com/apps/dependabot))
- Update dependencies [\#107](https://github.com/Materials-Consortia/optimade-gateway/pull/107) ([CasperWA](https://github.com/CasperWA))
- Update dependencies & GH Actions [\#104](https://github.com/Materials-Consortia/optimade-gateway/pull/104) ([CasperWA](https://github.com/CasperWA))
- Update dependencies and GH Actions [\#99](https://github.com/Materials-Consortia/optimade-gateway/pull/99) ([CasperWA](https://github.com/CasperWA))
- Update dependencies [\#96](https://github.com/Materials-Consortia/optimade-gateway/pull/96) ([CasperWA](https://github.com/CasperWA))
- Bump codecov/codecov-action from 1.5.0 to 1.5.2 [\#83](https://github.com/Materials-Consortia/optimade-gateway/pull/83) ([dependabot[bot]](https://github.com/apps/dependabot))
- Update dependencies + GH Actions [\#81](https://github.com/Materials-Consortia/optimade-gateway/pull/81) ([CasperWA](https://github.com/CasperWA))
- Update optimade\[server\] requirement from ~=0.14.0 to ~=0.15.0 [\#79](https://github.com/Materials-Consortia/optimade-gateway/pull/79) ([dependabot[bot]](https://github.com/apps/dependabot))
- Bump mkdocs-material from 7.1.3 to 7.1.4 [\#67](https://github.com/Materials-Consortia/optimade-gateway/pull/67) ([dependabot[bot]](https://github.com/apps/dependabot))
- Update auto-changelog-action to v1.4 [\#65](https://github.com/Materials-Consortia/optimade-gateway/pull/65) ([CasperWA](https://github.com/CasperWA))

## [v0.1.2](https://github.com/Materials-Consortia/optimade-gateway/tree/v0.1.2) (2021-05-01)

[Full Changelog](https://github.com/Materials-Consortia/optimade-gateway/compare/v0.1.1...v0.1.2)

**Fixed bugs:**

- CD is still wrong [\#63](https://github.com/Materials-Consortia/optimade-gateway/issues/63)

**Merged pull requests:**

- Fix tag version retrieval [\#64](https://github.com/Materials-Consortia/optimade-gateway/pull/64) ([CasperWA](https://github.com/CasperWA))

## [v0.1.1](https://github.com/Materials-Consortia/optimade-gateway/tree/v0.1.1) (2021-05-01)

[Full Changelog](https://github.com/Materials-Consortia/optimade-gateway/compare/v0.1.0...v0.1.1)

**Fixed bugs:**

- CD workflow not releasing latest documentation build [\#61](https://github.com/Materials-Consortia/optimade-gateway/issues/61)

**Merged pull requests:**

- Use ref variable for actions/checkout [\#62](https://github.com/Materials-Consortia/optimade-gateway/pull/62) ([CasperWA](https://github.com/CasperWA))

## [v0.1.0](https://github.com/Materials-Consortia/optimade-gateway/tree/v0.1.0) (2021-05-01)

[Full Changelog](https://github.com/Materials-Consortia/optimade-gateway/compare/5605131b4590b8b9b595714513199504e63e312c...v0.1.0)

**Implemented enhancements:**

- Create a /search endpoint [\#40](https://github.com/Materials-Consortia/optimade-gateway/issues/40)
- Sorting [\#20](https://github.com/Materials-Consortia/optimade-gateway/issues/20)
- Add test and update code for creating queries accordingly [\#38](https://github.com/Materials-Consortia/optimade-gateway/pull/38) ([CasperWA](https://github.com/CasperWA))
- Asynchronous queued queries [\#34](https://github.com/Materials-Consortia/optimade-gateway/pull/34) ([CasperWA](https://github.com/CasperWA))
- Add extra endpoints [\#27](https://github.com/Materials-Consortia/optimade-gateway/pull/27) ([CasperWA](https://github.com/CasperWA))
- Versioned base URLs [\#12](https://github.com/Materials-Consortia/optimade-gateway/pull/12) ([CasperWA](https://github.com/CasperWA))
- Dockerfile and docker-compose [\#11](https://github.com/Materials-Consortia/optimade-gateway/pull/11) ([CasperWA](https://github.com/CasperWA))
- Establish /gateways/{id}/structures endpoint [\#10](https://github.com/Materials-Consortia/optimade-gateway/pull/10) ([CasperWA](https://github.com/CasperWA))
- Tests and GET /gateways [\#7](https://github.com/Materials-Consortia/optimade-gateway/pull/7) ([CasperWA](https://github.com/CasperWA))

**Fixed bugs:**

- Make tests more loose for model assertion [\#24](https://github.com/Materials-Consortia/optimade-gateway/pull/24) ([CasperWA](https://github.com/CasperWA))

**Closed issues:**

- Documentation [\#53](https://github.com/Materials-Consortia/optimade-gateway/issues/53)
- Setup mock implementations for testing the gateway [\#32](https://github.com/Materials-Consortia/optimade-gateway/issues/32)
- Finalize the APIs - Determine fate of CLI [\#16](https://github.com/Materials-Consortia/optimade-gateway/issues/16)
- Further abstract and modularize the code [\#15](https://github.com/Materials-Consortia/optimade-gateway/issues/15)
- Update docker CI job [\#13](https://github.com/Materials-Consortia/optimade-gateway/issues/13)
- Don't use GH version of optimade package [\#8](https://github.com/Materials-Consortia/optimade-gateway/issues/8)

**Merged pull requests:**

- Change to v0.1.0-rc.1 [\#60](https://github.com/Materials-Consortia/optimade-gateway/pull/60) ([CasperWA](https://github.com/CasperWA))
- Don't sort for external DB requests [\#59](https://github.com/Materials-Consortia/optimade-gateway/pull/59) ([CasperWA](https://github.com/CasperWA))
- Update dependencies [\#58](https://github.com/Materials-Consortia/optimade-gateway/pull/58) ([CasperWA](https://github.com/CasperWA))
- Create documentation site [\#54](https://github.com/Materials-Consortia/optimade-gateway/pull/54) ([CasperWA](https://github.com/CasperWA))
- Update dependencies [\#52](https://github.com/Materials-Consortia/optimade-gateway/pull/52) ([CasperWA](https://github.com/CasperWA))
- Implement /databases for registering and handling known OPTIMADE databases [\#49](https://github.com/Materials-Consortia/optimade-gateway/pull/49) ([CasperWA](https://github.com/CasperWA))
- Change epfl-theos -\> Materials-Consortia & update codecov CI step [\#48](https://github.com/Materials-Consortia/optimade-gateway/pull/48) ([CasperWA](https://github.com/CasperWA))
- Update pytest-asyncio requirement from ~=0.14.0 to ~=0.15.0 [\#47](https://github.com/Materials-Consortia/optimade-gateway/pull/47) ([dependabot[bot]](https://github.com/apps/dependabot))
- Add license, copyright and funding information [\#46](https://github.com/Materials-Consortia/optimade-gateway/pull/46) ([CasperWA](https://github.com/CasperWA))
- Update dependencies [\#45](https://github.com/Materials-Consortia/optimade-gateway/pull/45) ([CasperWA](https://github.com/CasperWA))
- Set up the /search endpoint [\#41](https://github.com/Materials-Consortia/optimade-gateway/pull/41) ([CasperWA](https://github.com/CasperWA))
- Use pytest-httpx to mock external responses [\#39](https://github.com/Materials-Consortia/optimade-gateway/pull/39) ([CasperWA](https://github.com/CasperWA))
- Update optimade requirement from ~=0.13.3 to ~=0.14.0 [\#37](https://github.com/Materials-Consortia/optimade-gateway/pull/37) ([dependabot[bot]](https://github.com/apps/dependabot))
- Update httpx requirement from ~=0.17.0 to ~=0.17.1 [\#36](https://github.com/Materials-Consortia/optimade-gateway/pull/36) ([dependabot[bot]](https://github.com/apps/dependabot))
- Use latest MongoDB v4 \(v4.4\) [\#33](https://github.com/Materials-Consortia/optimade-gateway/pull/33) ([CasperWA](https://github.com/CasperWA))
- Update dependencies [\#31](https://github.com/Materials-Consortia/optimade-gateway/pull/31) ([CasperWA](https://github.com/CasperWA))
- Update httpx requirement from ~=0.16.1 to ~=0.17.0 [\#28](https://github.com/Materials-Consortia/optimade-gateway/pull/28) ([dependabot[bot]](https://github.com/apps/dependabot))
- Update dependencies [\#26](https://github.com/Materials-Consortia/optimade-gateway/pull/26) ([CasperWA](https://github.com/CasperWA))
- Update optimade and docker CI job [\#14](https://github.com/Materials-Consortia/optimade-gateway/pull/14) ([CasperWA](https://github.com/CasperWA))
- Various updates [\#9](https://github.com/Materials-Consortia/optimade-gateway/pull/9) ([CasperWA](https://github.com/CasperWA))
- Update dependencies [\#6](https://github.com/Materials-Consortia/optimade-gateway/pull/6) ([CasperWA](https://github.com/CasperWA))



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
