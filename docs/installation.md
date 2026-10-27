# Installation

## Requirements

- Linux with [Dank Material Shell](https://danklinux.com) (DMS).
- The **dmsProfiles** plugin, enabled. It provides the profiles and the picker.
- Python 3.11 or newer and `git`.
- `fzf` is optional: it powers the pickers of `install` and `remove` when you pass no argument.

The [Wallpaper Carousel](companion-plugins.md) plugin is optional but recommended.

## Install the tool

Pick one.

```sh
# uv
uv tool install omarchy-dms
uv tool upgrade omarchy-dms          # later, to update

# pipx
pipx install omarchy-dms

# pip (inside a virtual environment)
pip install omarchy-dms
```

Run it once without installing:

```sh
uvx omarchy-dms --help
```

From the repository, for the latest unreleased code:

```sh
uv tool install git+https://github.com/Villoh/omarchy-dms
pipx install git+https://github.com/Villoh/omarchy-dms
```

### Nix

```sh
nix run github:Villoh/omarchy-dms -- --help
```

To install it declaratively, add the flake as an input and use
`inputs.omarchy-dms.packages.${system}.default`. See [Omarchy's own themes](usage.md#omarchys-own-themes)
if you also want `sync`.

## Install the plugins

In DMS, open Settings → Plugins → Browse, or use the CLI:

```sh
dms plugins install dmsProfiles
dms plugins install wallpaperCarousel      # optional
```

Then enable them in Settings → Plugins. Details in [Companion plugins](companion-plugins.md).

## Check it works

```sh
omarchy-dms installed
```

It prints one line per theme (nothing yet on a fresh install) and exits 0. If you see
`error: dms not found in PATH`, DMS is not installed or not on your `PATH`.
