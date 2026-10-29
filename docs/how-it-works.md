# How it works

## Where things live

| What | Where |
|---|---|
| DMS theme folders | `~/.config/DankMaterialShell/themes/omarchy-<slug>/` |
| Wallpapers | `~/Pictures/Wallpapers/omarchy/<slug>/` |
| Where a community theme came from | `omarchy-<slug>/.source` |
| Marks one of Omarchy's own themes | `omarchy-<slug>/.builtin` |
| Profiles | owned by dmsProfiles, in `~/.config/DankMaterialShell/profiles/` |

`omarchy-dms` writes these folders itself, for both community themes (`install`) and Omarchy's own
(`sync`). A setup that deploys them as read-only symlinks instead (Nix does) also works: such
themes are only read, never rewritten or deleted.

## What a theme becomes

Omarchy themes are a directory with a `colors.toml` and a `backgrounds/` folder. `omarchy-dms`
turns the colors into a DMS custom theme and keeps the wallpapers as they are.

### Color mapping

Omarchy has no Material color roles, so the conversion is an approximation.

Two shapes of `colors.toml` exist in the wild and both are handled:

- The full palette: `accent`, `selection`, `muted`, `background`, `dark_background`,
  `darker_background`, `lighter_background`, `foreground`, `bright_foreground`, `red`, `yellow`,
  `blue`, `magenta`, ...
- A plain ANSI palette: `color0` to `color15`, plus `accent`, `background` and `foreground`.

Only `background`, `foreground` and `accent` are required. Anything missing is derived: the extra
background shades by mixing the background with black or white, and the error, warning, info and
secondary colors from the ANSI colors.

The theme is light when `mode = "light"` is set, or, if `mode` is absent, when the background is
brighter than half. DMS themes have a dark and a light variant; both use the same colors here, and
the profile sets which mode is active.

Roles: `primary` and `surfaceTint` take the accent; `surface` the background; `error`, `warning`
and `info` take red, yellow and blue; `primaryContainer` takes the selection color. Light themes
use darker shades of the background for containers, dark themes lighter ones.

Light themes are the most likely to need manual tweaks.

### Previews

DMS Browse shows an SVG card per theme. `omarchy-dms` writes `preview-dark.svg` and
`preview-light.svg` with the same layout DMS uses for registry themes, drawn with the theme's
colors. DMS only lists a theme when its folder is a real directory with a `theme.json`, which is
why built-in themes are linked file by file and not as one folder.

## Profiles

For each theme, `omarchy-dms`:

1. Pauses dmsProfiles autosave, so each change does not get written into the previously active
   profile. It is restored afterwards, also on errors.
2. Saves the **Original** profile if it does not exist yet.
3. Applies the theme, the mode and the first wallpaper, waiting for DMS to confirm each step, then
   creates the profile.
4. Sets the profile's [wallpaper folder](#the-wallpaper-folder).

DMS applies these asynchronously, so the tool polls `dms ipc call profiles list|status|snapshot`
until the state matches instead of sleeping for a fixed time. If DMS does not answer within about
15 seconds, it fails with `timed out waiting for ...`.

## The wallpaper folder

A profile stores one wallpaper, not a folder. The wallpaper picker of dmsProfiles
(`dms ipc call profiles wallpapers`) opens on the picture's folder, which is not always the theme's:
the profile keeps a copy of the picture, and you may choose one from elsewhere.

So `omarchy-dms` sets the **wallpaper folder** of each profile (`dms ipc call profiles folder
<slug> ~/Pictures/Wallpapers/omarchy/<slug>`), and the picker always opens on the theme's pictures.
`sync` also sets it on profiles that already exist, which is how profiles made by older versions
get it. Themes with no pictures in that folder are left alone.

Before 0.4, `omarchy-dms` registered an apply command (`omarchy-dms hook`) that pointed the
wallpaper back at the theme's folder after each switch. It is gone. If you have it set, clear it:

```sh
dms ipc call profiles setOption applyCommand ""
```
