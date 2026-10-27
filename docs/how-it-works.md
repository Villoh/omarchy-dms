# How it works

## Where things live

| What | Where |
|---|---|
| DMS theme folders | `~/.config/DankMaterialShell/themes/omarchy-<slug>/` |
| Wallpapers | `~/Pictures/Wallpapers/omarchy/<slug>/` |
| Where a theme came from | `omarchy-<slug>/.source` |
| Profiles | owned by dmsProfiles, in `~/.config/DankMaterialShell/profiles/` |

Built-in themes (Omarchy's own, deployed by Nix) are symlinks into the Nix store and read-only.
Community themes are real folders that `omarchy-dms` owns.

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
2. Registers the [apply command](#the-wallpaper-hook).
3. Saves the **Original** profile if it does not exist yet.
4. Applies the theme, the mode and the first wallpaper, waiting for DMS to confirm each step, then
   creates the profile.

DMS applies these asynchronously, so the tool polls `dms ipc call profiles list|status|snapshot`
until the state matches instead of sleeping for a fixed time. If DMS does not answer within about
15 seconds, it fails with `timed out waiting for ...`.

## The wallpaper hook

dmsProfiles stores one copy of the wallpaper inside each profile (plus a thumbnail). The
[Wallpaper Carousel](companion-plugins.md#wallpaper-carousel-optional-recommended) lists the
images in the folder of the current wallpaper, so after a profile switch it would find only that
copy.

`omarchy-dms` registers itself as the profile apply command (`profiles setOption applyCommand`).
After each switch, dmsProfiles runs `omarchy-dms hook` with `DMS_PROFILE_SLUG` set, and the hook
points the wallpaper back at the first image of `~/Pictures/Wallpapers/omarchy/<slug>/`. The
carousel then shows the whole theme.

dmsProfiles sets the profile's own wallpaper *after* running the apply command, so the hook starts
a detached process that waits 2 seconds before setting the wallpaper. The hook itself returns
immediately and does not delay the switch. It is the same image, so the change is not visible.

Profiles of themes with no folder in `~/Pictures/Wallpapers/omarchy/` are left alone.

With autosave on, dmsProfiles stores that wallpaper path in the profile. This does not change what
you see.
