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

1. Bump `version` in `pyproject.toml` (the Nix package reads it from there) and run `uv lock`.
2. Commit, then tag and push:

   ```sh
   git tag -s v0.2.1 -m v0.2.1 && git push origin v0.2.1
   ```

That is all: there are no release notes to write. `.github/workflows/release.yml` runs:

```
check-version -> ci -> build -> publish-pypi -> github-release
```

| Job | Does |
|---|---|
| `check-version` | The tag must equal the version in `pyproject.toml`. |
| `ci` | The full CI on the tagged commit. |
| `build` | Builds the sdist and wheel, installs the wheel in a clean environment and runs it. Keeps both as an artifact. |
| `publish-pypi` | Uploads exactly that artifact with [trusted publishing](https://docs.pypi.org/trusted-publishers/), no token. |
| `github-release` | Creates the GitHub release with the same files attached. |

### The release body

`.github/scripts/release_body.py <tag>` writes it, in two parts:

1. **What changed**, from the commits between the previous tag and this one. It reads
   [Conventional Commits](https://www.conventionalcommits.org/): `feat`, `fix`, `perf`, `docs` and
   `refactor` get a section each, breaking changes (`!` or a `BREAKING CHANGE` footer) go first, and
   `build`, `ci`, `chore`, `test`, `style` and `revert` are folded into a collapsed "Maintenance"
   block. Commits that do not follow the convention are listed under "Other changes". Each line links
   to its commit, and the body ends with a link to the full comparison.
2. **The sections every release carries**, from `.github/release-notes/_install.md`: how to install
   or upgrade, the Nix command, and links to the docs and to the exact version on PyPI. `{tag}` and
   `{version}` are replaced in it. To change what every release says, edit that file.

Because pull requests are squash-merged, the line you see is the PR title: write it as a
conventional commit.

To word one release by hand, put the text in `.github/release-notes/<tag>.md`; it replaces the
generated part for that tag (the Install section is still added). Preview any body locally:

```sh
GITHUB_REPOSITORY=Villoh/omarchy-dms python3 .github/scripts/release_body.py v0.2.0 --generated
```

A version published to PyPI cannot be reused.
