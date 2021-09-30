#!/usr/bin/env bash
set -e

echo -e "\n-o- Setting commit user -o-"
git config --local user.email "${GIT_USER_EMAIL}"
git config --local user.name "${GIT_USER_NAME}"

echo -e "\n-o- Update 'API Reference' docs -o-"
invoke create-api-reference-docs --pre-clean

echo -e "\n-o- Update 'index.md' landing page -o-"
invoke create-docs-index

echo -e "\n-o- Commit update - Documentation -o-"
git add docs/api_reference
git add docs/index.md
if [ -n "$(git status --porcelain docs/api_reference docs/index.md)" ]; then
    # Only commit if there's something to commit (git will return non-zero otherwise)
    git commit -m "Release ${GITHUB_REF#refs/tags/} - Documentation"
fi

echo -e "\n-o- Update version -o-"
invoke setver --ver="${GITHUB_REF#refs/tags/}"

echo -e "\n-o- Commit updates - Version & Changelog -o-"
git add optimade_gateway/__init__.py optimade_gateway/config.json tests/static/test_config.json
git add CHANGELOG.md
git commit -m "Release ${GITHUB_REF#refs/tags/} - Changelog"

echo -e "\n-o- Update version tag -o-"
TAG_MSG=.github/utils/release_tag_msg.txt
sed -i "s|TAG_NAME|${GITHUB_REF#refs/tags/}|" "${TAG_MSG}"
git tag -af -F "${TAG_MSG}" ${GITHUB_REF#refs/tags/}
