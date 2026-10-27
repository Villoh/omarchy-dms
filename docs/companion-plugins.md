# Companion plugins

`omarchy-dms` does not draw any interface of its own. It builds on two DMS plugins.

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

## Wallpaper Carousel (optional, recommended)

[Wallpaper Carousel](https://github.com/motor-dev/wallpaperCarousel) by yngwe is a fullscreen,
skewed carousel to browse and pick wallpapers. Choosing one also updates the shell's color
scheme.

It lists the images in the folder of the **current wallpaper**. Omarchy themes ship several
wallpapers each, so with `omarchy-dms` the carousel shows all of a theme's images and you switch
between them without changing the profile. Open it with:

```sh
dms ipc call wallpaperCarousel toggle
```

```
bind = SUPER CTRL SHIFT, SPACE, exec, dms ipc call wallpaperCarousel toggle
```

It also has `open`, `close`, `cycleNext` and `cyclePrevious`. Navigate with the arrow keys,
Enter applies, Escape closes.

Two things to know:

- DMS must manage your wallpaper. The carousel does not work with external wallpaper engines
  (swww, swaybg, hyprpaper). Enable it in DMS Settings → Wallpaper.
- dmsProfiles keeps a single copy of the wallpaper inside each profile, so after a profile switch
  the carousel would only see that one file. `omarchy-dms` fixes this with an
  [apply command](how-it-works.md#the-wallpaper-hook) that points the wallpaper back at the theme's folder.

## Install

```sh
dms plugins install dmsProfiles
dms plugins install wallpaperCarousel
```

Or from DMS Settings → Plugins → Browse. Enable both afterwards in Settings → Plugins.
