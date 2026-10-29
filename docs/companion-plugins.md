# Companion plugins

`omarchy-dms` does not draw any interface of its own. It builds on a DMS plugin.

## dmsProfiles (required)

[`dmsProfiles`](https://github.com/satoshoe-dev/dms-profiles) saves the complete look of the
shell (theme, accent, light or dark, wallpaper, bars, transparency, widgets) under a name and
switches between those looks, with an animated transition.

`omarchy-dms` creates one profile per Omarchy theme through the plugin's IPC
(`dms ipc call profiles ...`). Open the picker with:

```sh
dms ipc call profiles toggle
```

Bind that to a key, for example on Hyprland:

```
bind = SUPER CTRL, SPACE, exec, dms ipc call profiles toggle
```

The picker has four views (strip, free, carousel, grid) and several shapes; see the plugin's
settings, or `dms ipc call profiles setOption pickerView grid`.

## The wallpaper picker

Omarchy themes ship several wallpapers each. dmsProfiles has a picker for them: it opens on the
**wallpaper folder** of the active profile, you pick an image, and autosave stores it in that
profile. `omarchy-dms` sets the folder of each profile to `~/Pictures/Wallpapers/omarchy/<theme>/`
(`sync` also does it for profiles that already exist).

```sh
dms ipc call profiles wallpapers
```

```
bind = SUPER CTRL SHIFT, SPACE, exec, dms ipc call profiles wallpapers
```

It uses the picker view and shape you chose for profiles. DMS must manage your wallpaper (Settings
→ Wallpaper); external engines (swww, swaybg, hyprpaper) are not supported.

This needs a dmsProfiles with the `profiles folder` command. With an older one, `sync` stops with
`dmsProfiles too old`. The folder can also be changed by hand, in the plugin settings or with
`dms ipc call profiles folder <slug> <path>`.

## Install

```sh
dms plugins install dmsProfiles
```

Or from DMS Settings → Plugins → Browse. Enable it afterwards in Settings → Plugins.
