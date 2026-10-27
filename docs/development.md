# Development

```sh
git clone https://github.com/Villoh/omarchy-dms
cd omarchy-dms
uv sync
uv run python -m unittest discover -s tests
uv run ruff check . && uv run ruff format --check .
```

The tests use a stateful fake of `dms ipc`; they never touch a real DMS. They do call `git`, to
clone local repositories.

Layout: `src/omarchy_dms/` is the package (see [Library](library.md)), `tests/` the tests,
`.github/workflows/` the CI and release.

## Use it from Nix

The repository is a flake. `packages.default` builds the CLI, running the tests in the build.

```nix
inputs.omarchy-dms = {
  url = "github:Villoh/omarchy-dms";
  inputs.nixpkgs.follows = "nixpkgs";
};
```

This is optional. Without it `sync` downloads Omarchy's themes itself, as on any other distribution.
To pin them to a flake input instead, and to deploy the theme folders declaratively, wrap the package
so `OMARCHY_THEMES` is set:

```nix
pkgs.symlinkJoin {
  name = "omarchy-dms";
  paths = [ inputs.omarchy-dms.packages.${pkgs.stdenv.hostPlatform.system}.default ];
  nativeBuildInputs = [ pkgs.makeWrapper ];
  postBuild = "wrapProgram $out/bin/omarchy-dms --set OMARCHY_THEMES ${inputs.omarchy}/themes";
}
```

with `omarchy = { url = "github:basecamp/omarchy"; flake = false; };` as another input. The
theme folders can then be generated at build time with `omarchy-dms render`, and deployed to
`~/.config/DankMaterialShell/themes/omarchy-<name>/` as individual files (not as one linked
folder; see [previews](how-it-works.md#previews)).

## CI

`.github/workflows/ci.yml` runs on every push and pull request: lint and lockfile, tests on
Python 3.11 to 3.14, and the Nix build.

## Releasing

Releases are cut from `main` by the `Release` workflow, and nothing has to be edited by hand:
it raises the version, commits it, tags it and publishes.

```sh
gh workflow run release.yml -f bump=patch     # or minor, or major
```

Or in GitHub: Actions → Release → Run workflow, and choose `patch`, `minor` or `major`. It must be
run from `main`.

```
checks -> bump -> build -> publish-pypi -> github-release
```

| Job | Does |
|---|---|
| `checks` | The full CI (`ci.yml`) must pass on `main`. Nothing is pushed if it fails. |
| `bump` | Raises the version in `pyproject.toml` and `uv.lock` (`uv version --bump`), commits `chore: release X.Y.Z` to `main` and tags `vX.Y.Z`, in one atomic push. |
| `build` | Builds the sdist and wheel from the tag, installs the wheel in a clean environment and checks that it reports the new version. Keeps both as an artifact. |
| `publish-pypi` | Uploads exactly that artifact with [trusted publishing](https://docs.pypi.org/trusted-publishers/), no token. |
| `github-release` | Creates the GitHub release with the same files attached. |

The version commit is made by `github-actions[bot]`, so it is not GPG-signed. If a job after `bump`
fails, the version commit and the tag are already on `main`: fix the cause and re-run the failed
jobs of that run rather than starting a new release.

### The release body

It is GitHub's generated notes plus a short footer:

- **The notes** list the pull requests merged since the previous tag, grouped by label as set in
  `.github/release.yml` (`enhancement`, `bug`, `documentation`, anything else under "Other
  changes"), with author and link. Work through pull requests and squash-merge them: the PR
  title is the line that appears, so write it as a conventional commit (`feat: ...`). Commits
  pushed straight to `main` do not show up.
- **The footer** is `.github/release-footer.md`: how to install or upgrade and the link to the
  docs of that version (`{tag}` is replaced). Edit that file to change what every release says.

A version published to PyPI cannot be reused.
