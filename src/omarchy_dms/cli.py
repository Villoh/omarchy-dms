"""Command line frontend over ops.Omarchy."""

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, theme
from .dms import Dms, DmsError
from .ops import Omarchy, store_repos
from .store import Store, StoreError

HOME = Path.home()
THEMES = HOME / ".config/DankMaterialShell/themes"
WALLPAPERS = HOME / "Pictures/Wallpapers/omarchy"


def _hook_command():
    exe = shutil.which("omarchy-dms")
    return f"{shlex.quote(exe)} hook" if exe else f"{shlex.quote(sys.executable)} -m omarchy_dms hook"


def _pick(items, prompt, multi):
    if not shutil.which("fzf"):
        raise StoreError("fzf not found: pass the name(s) as arguments")
    cmd = ["fzf", "--prompt", prompt, *(["-m"] if multi else [])]
    r = subprocess.run(cmd, input="\n".join(items), text=True, stdout=subprocess.PIPE, check=False)
    return r.stdout.split()


def _table(header, rows):
    """Print aligned columns. On a terminal: a bold header, and `installed` in green."""
    tty = sys.stdout.isatty()
    color = tty and "NO_COLOR" not in os.environ
    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header) - 1)]

    def line(row, style=""):
        cells = [c.ljust(w) for c, w in zip(row, widths, strict=False)]
        last = f"\033[{style}m{row[-1]}\033[0m" if color and style else row[-1]
        return "  ".join([*cells, last]).rstrip()

    if tty:
        print(line(header, "1"))
    for r in rows:
        print(line(r, "32" if r[-1] == "installed" else ""))


def _parser():
    p = argparse.ArgumentParser(prog="omarchy-dms", description="Omarchy themes as DMS profiles.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser(
        "sync",
        help="create profiles for Omarchy's own themes (downloaded unless OMARCHY_THEMES is set)",
    )
    s.add_argument("--force", action="store_true", help="recreate the profiles and theme files that exist")
    s.add_argument("themes", nargs="*")
    s = sub.add_parser("install", help="install a community theme and create its profile")
    s.add_argument("repo", nargs="?", help="owner/repo or git URL (none: pick from omarchy.org/themes)")
    s = sub.add_parser("update", help="refresh themes installed with install (all, or the ones named)")
    s.add_argument("themes", nargs="*")
    s = sub.add_parser("remove", help="remove theme, wallpapers and profile (none named: pick with fzf)")
    s.add_argument("-y", "--yes", action="store_true", help="do not ask")
    s.add_argument("themes", nargs="*")
    sub.add_parser("list", aliases=["installed"], help="the themes you have: origin and whether they have a profile")
    s = sub.add_parser("search", help="find themes on omarchy.org/themes by name or repo")
    s.add_argument("text", nargs="?", default="", help="part of the theme name or repo")
    s.add_argument("--owner", default="", metavar="USER", help="only repos of this GitHub user")
    s.add_argument("--available", action="store_true", help="hide the ones you already have")
    s.add_argument("--all", action="store_true", help="no text needed: every theme in the store")
    s.add_argument("--limit", type=int, metavar="N", help="show at most N themes")
    s = sub.add_parser("render", help="convert a colors.toml into a DMS theme folder")
    s.add_argument("colors")
    s.add_argument("slug")
    s.add_argument("outdir")
    sub.add_parser("hook", help="dmsProfiles apply command (reads DMS_PROFILE_SLUG)")
    return p


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    if args.cmd == "search":
        if not (args.text or args.owner or args.all):
            parser.error("search needs some text, --owner USER or --all")
        if args.limit is not None and args.limit < 1:
            parser.error("--limit must be at least 1")
    builtin = Path(os.environ["OMARCHY_THEMES"]) if os.environ.get("OMARCHY_THEMES") else None
    omarchy = Omarchy(Dms(), Store(THEMES, WALLPAPERS), builtin, _hook_command())
    try:
        match args.cmd:
            case "sync":
                omarchy.sync(args.themes, args.force)
            case "install":
                repo = args.repo or next(iter(_pick(store_repos(), "omarchy theme> ", False)), None)
                if repo:
                    omarchy.install(repo)
            case "update":
                return 1 if omarchy.update(args.themes) else 0
            case "remove":
                names = args.themes or _pick(omarchy.store.slugs(), "remove (Tab marks)> ", True)
                if names and not args.yes:
                    print(f"remove: {' '.join(names)}")
                    if input("continue? [y/N] ") != "y":
                        return 0
                if names:
                    omarchy.remove(names)
            case "list" | "installed":
                _table(
                    ("NAME", "PROFILE", "SOURCE"),
                    [
                        (r.slug, "yes" if r.profile else "-", r.origin or "community (no .source: reinstall to track)")
                        for r in omarchy.installed()
                    ],
                )
            case "search":
                found = omarchy.available(args.text, args.owner, args.available)
                shown = found[: args.limit]
                if sys.stdout.isatty():
                    _table(("NAME", "REPO", "STATE"), [(s, r, "installed" if h else "") for s, r, h in shown])
                else:  # piped: plain owner/repo, one per line
                    print("\n".join(r for _, r, _ in shown))
                if len(shown) < len(found):
                    print(f"showing {len(shown)} of {len(found)}", file=sys.stderr)
            case "render":
                theme.render(args.colors, args.slug, args.outdir)
            case "hook":
                omarchy.hook(os.environ.get("DMS_PROFILE_SLUG", ""))
    except (DmsError, StoreError, theme.ThemeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0
