# Usage

```
omarchy-dms install [owner/repo | git URL]
omarchy-dms list
omarchy-dms search [text] [--owner USER] [--available] [--all] [--limit N]
omarchy-dms update [theme ...]
omarchy-dms remove [-y] [theme ...]
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

## list

The themes you have. Works offline. (`installed` is an older name for the same command.)

```
$ omarchy-dms list
NAME        PROFILE  SOURCE
dracula     yes      https://github.com/catlee/omarchy-dracula-theme
gruvbox     yes      built-in
periphery   -        community (no .source: reinstall to track)
```

Columns: the theme name (what `update` and `remove` take), whether it has a profile, and where it comes
from: `built-in` (one of Omarchy's own, see [sync](#sync-omarchys-own-themes)), the repository URL, or no
`.source` (installed before the tool tracked origins).

## update

Fetches installed community themes again and rewrites their files.

```sh
omarchy-dms update              # all of them
omarchy-dms update dracula      # just this one (owner/repo works too)
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
omarchy-dms remove -y dracula nord  # owner/repo works too
omarchy-dms remove                  # pick with fzf; Tab marks several
```

- If the profile being removed is the active one, it switches to **Original** first.
- A [built-in](#sync-omarchys-own-themes) theme written by `sync` is deleted like any other and `sync` brings it back; one deployed read-only (for example by Nix) only loses its profile.
- Names are checked against the theme folders that exist, so nothing else is ever deleted.

## search

Looks in the themes listed on [omarchy.org/themes](https://omarchy.org/themes/). It needs something
to look for: some text (matched against the name and the repository), `--owner USER`, or `--all`.

| Flag | Does |
|---|---|
| `--owner USER` | Only repositories of this GitHub user. |
| `--available` | Hides the themes you already have. |
| `--limit N` | Shows at most N themes, and says on stderr how many matched (`showing 10 of 218`). |
| `--all` | No text needed: every theme in the store. To browse them, `omarchy-dms install` with no argument opens an fzf picker. |

```
$ omarchy-dms search drac
NAME          REPO                                   STATE
drac          ShehabShaef/omarchy-drac-theme
dracula       catlee/omarchy-dracula-theme           installed
flat-dracula  OldJobobo/omarchy-flat-dracula-theme
```

`NAME` is what `update` and `remove` take, `REPO` what `install` takes. When piped it prints just
`owner/repo`, one per line. It does not check which ones have a `colors.toml`.

## sync: Omarchy's own themes

Omarchy itself ships a set of themes (the `themes/` directory of
[`basecamp/omarchy`](https://github.com/basecamp/omarchy)). `sync` creates a profile for each.

```sh
omarchy-dms sync                 # every theme
omarchy-dms sync nord gruvbox    # just these
omarchy-dms sync --force         # also rewrite files and profiles that already exist
```

With nothing else set up, `sync` downloads what it needs: a partial clone of the Omarchy
repository that fetches only each theme's `colors.toml` and still wallpapers (about 140 MB, a few
seconds; the intro videos are skipped), kept in a temporary directory. For each theme it then
writes the DMS theme folder and the wallpapers exactly like `install` does, and creates the profile.

- Themes and profiles that already exist are skipped. `--force` rewrites them, which is also how
  you pick up changes after Omarchy updates a theme.
- To work offline or from a pinned version, point `OMARCHY_THEMES` at the `themes/` directory of a
  checkout; nothing is downloaded then.
- If the theme folders were deployed by something else as read-only symlinks (a Nix configuration
  does this), `sync` uses them as they are and only creates profiles. `--force` does not rewrite
  them.
- `update` does not apply to these themes; use `sync --force`.

## render

`omarchy-dms render COLORS_TOML NAME OUTDIR` converts one `colors.toml` into a DMS theme folder
(`theme.json` plus the previews) without touching DMS or copying wallpapers. It exists for
declarative setups that generate the folders at build time; day to day, `sync` and `install` do it. See
[color mapping](how-it-works.md#color-mapping).

## hook

`omarchy-dms hook` is not meant to be run by hand. It is the profile *apply command* that
dmsProfiles runs after a switch; see [the wallpaper hook](how-it-works.md#the-wallpaper-hook).
