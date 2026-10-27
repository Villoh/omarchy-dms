#!/usr/bin/env bash
# Prints the body of the GitHub release for a tag, in two parts:
#
#   1. the notes for this version: .github/release-notes/<tag>.md if it exists,
#      otherwise the ones GitHub generates from merged pull requests
#   2. the fixed sections every release carries (.github/release-notes/_install.md),
#      where {tag} and {version} are replaced
#
# usage: release-body.sh TAG
# The generated notes need GH_TOKEN and GITHUB_REPOSITORY in the environment.
set -euo pipefail

tag=${1:?usage: release-body.sh TAG}
version=${tag#v}
dir="$(cd "$(dirname "$0")/.." && pwd)/release-notes"

if [ -f "$dir/$tag.md" ]; then
  cat "$dir/$tag.md"
else
  gh api -X POST "repos/${GITHUB_REPOSITORY}/releases/generate-notes" -f tag_name="$tag" --jq .body
fi

printf '\n'
sed -e "s/{tag}/$tag/g" -e "s/{version}/$version/g" "$dir/_install.md"
