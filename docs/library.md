# Library

The CLI is a thin layer over an importable package. A different frontend (a TUI, a script, a
service) can use it directly instead of running `omarchy-dms` as a process.

```python
from omarchy_dms import Dms, Omarchy, Store

omarchy = Omarchy(
    Dms(),
    Store(themes_dir, wallpapers_dir),
    hook_command="omarchy-dms hook",
    log=print,
)
omarchy.install("catlee/omarchy-dracula-theme")
```

The API never exits the process: failures are exceptions, and progress goes to the `log`
callback (it defaults to `print`; pass `lambda _: None` for silence).

## Modules

| Module | Role |
|---|---|
| `omarchy_dms.theme` | `colors.toml` to a DMS theme. Pure: no DMS, no network. |
| `omarchy_dms.dms` | Client for `dms ipc`. |
| `omarchy_dms.store` | Theme folders and wallpapers on disk, and fetching community themes. |
| `omarchy_dms.ops` | The operations the CLI exposes. |
| `omarchy_dms.cli` | `argparse` frontend over `ops`. |

The package root re-exports `Dms`, `DmsError`, `Omarchy`, `Row`, `Store`, `StoreError`, `Theme`,
`ThemeError`, `resolve_repo` and `store_repos`.

## Omarchy

`Omarchy(dms, store, builtin_dir=None, hook_command="omarchy-dms hook", log=print, settle=1.0, sleep=time.sleep)`

| Method | Returns | Does |
|---|---|---|
| `installed()` | `list[Row]` | Every theme: `slug`, `profile` (bool), `origin` (`"built-in"`, a URL, or `""`). |
| `sync(names=(), force=False)` | | Profiles for Omarchy's own themes. Needs `builtin_dir`. |
| `install(arg)` | the slug | Install a community theme from `owner/repo` or a git URL. |
| `update(names=())` | slugs that failed | Fetch installed community themes again. |
| `remove(names)` | | Delete themes (built-ins only lose their profile). |
| `hook(slug)` | | The apply command: set the wallpaper back to the theme folder, detached. |

## Dms

`Dms(runner=run_dms, sleep=time.sleep, attempts=60, interval=0.25, spawn=subprocess.Popen)`

The only place that starts a process is `runner`, a callable that takes the `dms` arguments and
returns its output. Replace it to talk to DMS another way, or to test. Methods: `profiles()`,
`find_profile(slug, name)`, `status()`, `active()`, `snapshot()`, `set_option()`,
`autosave_paused()` (a context manager), `create_profile()`, `remove_profile()`, `apply_profile()`,
`custom_theme()`, `set_mode()`, `set_wallpaper()`, `set_wallpaper_later()`.

Calls that DMS finishes asynchronously wait until the result shows up, up to
`attempts * interval` seconds, then raise `DmsError`.

## Store

`Store(themes_dir, wall_dir)` knows the folder layout: `slugs()`, `themes()`, `images(slug)`,
`source(slug)`, `is_builtin(slug)`, `fetch(url, slug)` (clone and write; returns the mode) and
`remove(slug)`. `resolve_repo(arg)` turns `owner/repo` or a git URL into `(url, slug)`.

## Errors

| Exception | Raised for |
|---|---|
| `DmsError` | `dms` missing, failing, or not reaching the expected state in time. |
| `StoreError` | Bad repository or theme name, no `colors.toml`, unknown theme, clone failed. |
| `ThemeError` | A `colors.toml` that cannot be read or has a bad color. |

## Writing a test

The test suite drives a stateful fake of `dms ipc` through the `runner`; see
`tests/test_omarchy_dms.py`. Nothing in it touches a real shell.
