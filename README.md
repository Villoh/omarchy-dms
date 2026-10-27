# omarchy-dms

Use [Omarchy](https://omarchy.org) themes in [Dank Material Shell](https://danklinux.com)
as [dmsProfiles](https://github.com/satoshoe-dev/dms-profiles) looks: colors, wallpapers
and light/dark mode, switchable from the profile picker.

It converts an Omarchy `colors.toml` into a DMS custom theme (with the Browse previews),
copies the theme's wallpapers, and creates one profile per theme through `dms ipc`.
Themes from the [omarchy.org/themes](https://omarchy.org/themes/) store install with one command.

## Requirements

DMS with the `dmsProfiles` plugin enabled, Python 3.11+, `git`, and optionally `fzf`
(pickers). No other dependencies.

## Install

```sh
pipx install omarchy-dms
# or, from the repository
pipx install git+https://github.com/Villoh/omarchy-dms
```

On Nix: `nix run github:Villoh/omarchy-dms`.

## Usage

```sh
omarchy-dms install                      # pick from the omarchy.org/themes store (fzf)
omarchy-dms install owner/repo           # or a repo / git URL
omarchy-dms installed                    # every theme, its origin, and whether it has a profile
omarchy-dms update [theme...]            # refetch installed themes (all, or the ones named)
omarchy-dms remove [-y] [theme...]       # theme, wallpapers and profile (no names: fzf, Tab marks)
omarchy-dms list                         # repos listed on the store
omarchy-dms sync [--force] [theme...]    # profiles for Omarchy's own themes (see below)
```

Themes land in `~/.config/DankMaterialShell/themes/omarchy-<name>/` and wallpapers in
`~/Pictures/Wallpapers/omarchy/<name>/`. Only themes with a `colors.toml` work; alacritty-only
themes are rejected.

**Own themes.** `sync` needs Omarchy's own `themes/` directory, given by `OMARCHY_THEMES`
(for example a checkout of `basecamp/omarchy`), with the theme folders already in place
for DMS: `omarchy-dms render <colors.toml> <name> <outdir>` writes one.

**Wallpaper carousel.** dmsProfiles stores one wallpaper copy per profile. The CLI registers
itself as the profile *apply command* so that, after a switch, the wallpaper points back at the
theme's folder and a carousel lists all of its images.

## As a library

`omarchy_dms.Omarchy(dms, store, ...)` is the API behind the CLI: it never prints or exits,
progress goes to a `log` callback and failures are exceptions (`DmsError`, `StoreError`,
`ThemeError`). Another frontend can import it instead of running the CLI.

```python
from omarchy_dms import Dms, Omarchy, Store

omarchy = Omarchy(Dms(), Store(themes_dir, wallpapers_dir), log=print)
omarchy.install("owner/omarchy-example-theme")
```

## Development

```sh
uv sync
uv run python -m unittest discover -s tests
uv run ruff check . && uv run ruff format --check .
```

## Releasing

Bump `version` in `pyproject.toml` (the Nix package reads it from there), commit, then tag it:

```sh
git tag v0.1.0 && git push origin v0.1.0
```

The `CD` workflow checks the tag against the version, runs CI (including the Nix build), publishes
to PyPI with trusted publishing and creates the GitHub release.

The tests drive a stateful fake of `dms ipc`; nothing touches a real shell.

## License

[MIT](LICENSE)
