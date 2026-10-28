# omarchy-dms

Use [Omarchy](https://omarchy.org) themes in [Dank Material Shell](https://danklinux.com) as
[dmsProfiles](https://github.com/satoshoe-dev/dms-profiles) looks: colors, wallpapers and
light/dark mode, switchable from the profile picker.

It converts an Omarchy `colors.toml` into a DMS custom theme (with the Browse previews), copies the
theme's wallpapers and creates one profile per theme through `dms ipc`. Themes from the
[omarchy.org/themes](https://omarchy.org/themes/) store install with one command.

## Install

```sh
uv tool install omarchy-dms     # or: pipx install omarchy-dms
```

You also need DMS with the **dmsProfiles** plugin, and, optionally, **Wallpaper Carousel**. See
[Installation](https://github.com/Villoh/omarchy-dms/blob/main/docs/installation.md).

## Quick start

```sh
omarchy-dms sync                         # profiles for Omarchy's own themes (downloaded for you)
omarchy-dms install                      # pick a theme from the omarchy.org/themes store (fzf)
omarchy-dms install owner/repo           # or a repository / git URL
omarchy-dms list                         # the themes you have, their origin, and whether they have a profile
omarchy-dms search text                  # find themes on omarchy.org/themes (--owner, --available, --all)
omarchy-dms update [theme...]            # refetch installed themes
omarchy-dms remove [-y] [theme...]       # theme, wallpapers and profile
```

Then open the profile picker:

```sh
dms ipc call profiles toggle
```

Installing a theme applies it, and your previous look is saved as a profile called **Original**.

## Works with

- **[dmsProfiles](https://github.com/satoshoe-dev/dms-profiles)** (required): stores and switches
  the looks.
- **[Wallpaper Carousel](https://github.com/motor-dev/wallpaperCarousel)** (optional): browse every
  wallpaper of the active theme. `omarchy-dms` keeps the wallpaper pointing at the theme's folder
  so the carousel lists them all. See [Companion plugins](https://github.com/Villoh/omarchy-dms/blob/main/docs/companion-plugins.md).

## Documentation

| | |
|---|---|
| [Installation](https://github.com/Villoh/omarchy-dms/blob/main/docs/installation.md) | requirements, `uv tool`, pipx, pip, Nix, plugins |
| [Usage](https://github.com/Villoh/omarchy-dms/blob/main/docs/usage.md) | every command in detail |
| [Companion plugins](https://github.com/Villoh/omarchy-dms/blob/main/docs/companion-plugins.md) | dmsProfiles and Wallpaper Carousel |
| [How it works](https://github.com/Villoh/omarchy-dms/blob/main/docs/how-it-works.md) | color mapping, profiles, the wallpaper hook, file layout |
| [Library](https://github.com/Villoh/omarchy-dms/blob/main/docs/library.md) | use it from Python instead of the CLI |
| [Development](https://github.com/Villoh/omarchy-dms/blob/main/docs/development.md) | tests, Nix, CI, releasing |

## Limits

- Only themes that ship a `colors.toml` work; alacritty-only themes are rejected.
- Omarchy has no Material color roles, so the conversion is an approximation; light themes are the
  most likely to need tweaks.
- Linux with DMS. Nix is optional: it works the same on Arch, Fedora, NixOS and the rest. Developed
  on NixOS; reports from other distributions are welcome.

## License

[MIT](https://github.com/Villoh/omarchy-dms/blob/main/LICENSE)
