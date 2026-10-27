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
    sub.add_parser("installed", help="every theme, where it comes from, profile or not")
    sub.add_parser("list", help="repos listed on omarchy.org/themes")
    s = sub.add_parser("render", help="convert a colors.toml into a DMS theme folder")
    s.add_argument("colors")
    s.add_argument("slug")
    s.add_argument("outdir")
    sub.add_parser("hook", help="dmsProfiles apply command (reads DMS_PROFILE_SLUG)")
    return p


def main(argv=None):
    args = _parser().parse_args(argv)
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
            case "installed":
                for row in omarchy.installed():
                    origin = row.origin or "community (no .source: reinstall to track)"
                    print(f"{row.slug:<22} {'profile' if row.profile else '-':<8} {origin}")
            case "list":
                print("\n".join(store_repos()))
            case "render":
                theme.render(args.colors, args.slug, args.outdir)
            case "hook":
                omarchy.hook(os.environ.get("DMS_PROFILE_SLUG", ""))
    except (DmsError, StoreError, theme.ThemeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0
