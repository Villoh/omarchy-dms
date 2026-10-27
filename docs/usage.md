# Usage

```
omarchy-dms install [owner/repo | git URL]
omarchy-dms installed
omarchy-dms update [theme ...]
omarchy-dms remove [-y] [theme ...]
omarchy-dms list
omarchy-dms sync [--force] [theme ...]
omarchy-dms render COLORS_TOML NAME OUTDIR
omarchy-dms hook
```

Errors print `error: ...` to stderr and exit with status 1.

A *theme* is named by its **slug**: the repository name without the `omarchy-` prefix and the
`-theme` suffix, lowercased. `catlee/omarchy-dracula-theme` is `dracula`; its profile is called
"Dracula".

## install

Installs a community theme and creates its profile.

```sh
omarchy-dms install                              # pick from the omarchy.org/themes store (needs fzf)
omarchy-dms install catlee/omarchy-dracula-theme # owner/repo
omarchy-dms install https://github.com/r-bart/omarchy-periphery-theme.git
```

What it does, in order:

1. Clones the repository (shallow). It must contain a `colors.toml`; alacritty-only themes are
   rejected.
2. Writes `~/.config/DankMaterialShell/themes/omarchy-<slug>/` with `theme.json`, the two preview
   SVGs the DMS Browse tab shows, and a `.source` file holding the repository URL.
3. Copies the repository's `backgrounds/` images (jpg, jpeg, png, webp; tiny placeholders are
   skipped) to `~/Pictures/Wallpapers/omarchy/<slug>/`.
4. Applies the theme: custom theme, light or dark mode, and the first wallpaper.
5. Creates the profile.

> Step 4 changes your current look. Before the first change, `omarchy-dms` saves your look as a
> profile called **Original**, so you can go back to it from the picker.

Installing a theme that is already installed refreshes its files and recreates its profile.

## installed

```
$ omarchy-dms installed
dracula                profile  https://github.com/catlee/omarchy-dracula-theme
gruvbox                profile  built-in
periphery              -        community (no .source: reinstall to track)
```

Columns: slug, whether it has a profile, and where it comes from: `built-in` (Omarchy's own, see
below), the repository URL, or no `.source` (installed before the tool tracked origins).

## update

Fetches installed community themes again and rewrites their files.

```sh
omarchy-dms update              # all of them
omarchy-dms update dracula      # just this one
```

- Themes without a `.source` are skipped with a message; reinstall them once with `install`.
- Profiles are not touched. They point at `theme.json` by path, so the colors follow. A profile
  also keeps its own copy of one wallpaper; run `install` again to refresh that.
- A repository that fails to download is reported and the others continue. The exit status is 1 if
  any failed.

## remove

Deletes a theme: its folder, its wallpapers and its profile.

```sh
omarchy-dms remove dracula          # asks "continue? [y/N]"
omarchy-dms remove -y dracula nord
omarchy-dms remove                  # pick with fzf; Tab marks several
```

- If the profile being removed is the active one, it switches to **Original** first.
- A [built-in](#omarchys-own-themes) theme only loses its profile; its files are managed by Nix.
- Names are checked against the theme folders that exist, so nothing else is ever deleted.

## list

Prints the repositories listed on [omarchy.org/themes](https://omarchy.org/themes/), as
`owner/repo`, one per line. It does not check which ones have a `colors.toml`.

## Omarchy's own themes

Omarchy itself ships a set of themes (the `themes/` directory of `basecamp/omarchy`).
`sync` creates profiles for them. It needs:

- `OMARCHY_THEMES` pointing at that `themes/` directory (for example a checkout of
  `basecamp/omarchy`).
- The theme folders already present in DMS, one per theme. `render` writes one:

```sh
omarchy-dms render "$OMARCHY_THEMES/nord/colors.toml" nord ~/.config/DankMaterialShell/themes/omarchy-nord
```

```sh
omarchy-dms sync                 # every theme
omarchy-dms sync nord gruvbox    # just these
omarchy-dms sync --force         # recreate profiles that already exist
```

Existing profiles are skipped unless you pass `--force`. On NixOS this can be done declaratively;
see [development](development.md#use-it-from-nix).

## render

`omarchy-dms render COLORS_TOML NAME OUTDIR` converts one `colors.toml` into a DMS theme folder
(`theme.json` plus the previews) without touching DMS. See
[color mapping](how-it-works.md#color-mapping).

## hook

`omarchy-dms hook` is not meant to be run by hand. It is the profile *apply command* that
dmsProfiles runs after a switch; see [the wallpaper hook](how-it-works.md#the-wallpaper-hook).
