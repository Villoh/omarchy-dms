"""What omarchy-dms does, as an API: sync, install, update, remove, installed, hook.

No printing and no exiting: progress goes to `log`, problems are exceptions
(DmsError, StoreError, ThemeError), results are returned.
"""

import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import theme
from .dms import Dms
from .store import Store, StoreError, resolve_repo

STORE_URL = "https://omarchy.org/themes/"
NOT_COMMUNITY = {"basecamp", "omacom"}


@dataclass(frozen=True)
class Row:
    slug: str
    profile: bool
    origin: str  # "built-in", the repo URL, or "" for a community theme with no .source


def store_repos():
    """Repos listed on omarchy.org/themes, as owner/repo."""
    req = urllib.request.Request(STORE_URL, headers={"User-Agent": "omarchy-dms"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (fixed https URL)
            html = r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as e:
        raise StoreError(f"{STORE_URL}: {e}") from e
    repos = set(re.findall(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", html))
    return sorted(r for r in repos if r.split("/")[0] not in NOT_COMMUNITY)


class Omarchy:
    def __init__(
        self,
        dms: Dms,
        store: Store,
        builtin_dir: Path | None = None,
        hook_command: str = "omarchy-dms hook",
        log: Callable[[str], None] = print,
        settle: float = 1.0,
        sleep=time.sleep,
    ):
        self.dms = dms
        self.store = store
        self.builtin_dir = Path(builtin_dir) if builtin_dir else None
        self.hook_command = hook_command
        self.log = log
        self.settle = settle
        self._sleep = sleep

    # -- internals
    @contextmanager
    def _session(self):
        """Autosave off, the wallpaper hook registered, and a way back (Original)."""
        with self.dms.autosave_paused():
            self.dms.set_option("applyCommand", self.hook_command)
            if not self.dms.find_profile("original", "Original"):
                self.log("create: Original")
                self.dms.create_profile("Original")
            yield

    def _make(self, slug, mode, force):
        name = theme.profile_name(slug)
        existing = self.dms.find_profile(slug, name)
        if existing:
            if not force:
                self.log(f"skip: {name}")
                return
            self.dms.remove_profile(existing["slug"])
        if not self.store.theme_json(slug).is_file():
            raise StoreError(f"{slug}: theme folder missing (deploy the Home Manager config first)")
        self.dms.custom_theme(self.store.theme_json(slug), f"omarchy-{slug}")
        self.dms.set_mode(mode)
        images = self.store.images(slug)
        if images:
            self.dms.set_wallpaper(images[0])
        self._sleep(self.settle)
        self.log(f"create: {name}")
        self.dms.create_profile(name)

    # -- operations
    def installed(self):
        names = {p.get("slug") for p in self.dms.profiles()} | {p.get("name") for p in self.dms.profiles()}
        return [
            Row(t.slug, t.slug in names or theme.profile_name(t.slug) in names,
                "built-in" if t.builtin else (t.source or ""))
            for t in self.store.themes()
        ]

    def sync(self, names=(), force=False):
        """Profiles for Omarchy's own themes (all, or the ones named)."""
        if not self.builtin_dir or not self.builtin_dir.is_dir():
            raise StoreError("Omarchy's own themes are not available (OMARCHY_THEMES is not set)")
        available = {p.parent.name: p for p in sorted(self.builtin_dir.glob("*/colors.toml"))}
        unknown = [n for n in names if n not in available]
        if unknown:
            raise StoreError(f"not an Omarchy theme: {', '.join(unknown)}")
        with self._session():
            for slug, colors in available.items():
                if not names or slug in names:
                    self._make(slug, theme.mode_of(theme.load_palette(colors)), force)

    def install(self, arg):
        """Install a community theme (owner/repo or git URL); returns its slug."""
        url, slug = resolve_repo(arg)
        mode = self.store.fetch(url, slug)
        with self._session():
            self._make(slug, mode, force=True)  # reinstalling refreshes the profile
        return slug

    def update(self, names=()):
        """Refetch installed community themes; returns the slugs that failed.

        Profiles are left alone: they point at theme.json by path, so the colors
        follow; `install` again to also refresh a profile's own wallpaper copy.
        """
        by_slug = {t.slug: t for t in self.store.themes()}
        for n in names:
            if n not in by_slug or not by_slug[n].source:
                self.log(f"not updatable (no .source): {n}")
        targets = [t for t in by_slug.values() if t.source and (not names or t.slug in names)]
        if not targets and not names:
            self.log("no installed community themes (reinstall them once with: omarchy-dms install <repo>)")
        failed = []
        for t in targets:
            self.log(f"update: {t.slug} ({t.source})")
            try:
                self.store.fetch(t.source, t.slug)
            except (StoreError, theme.ThemeError) as e:
                self.log(f"failed: {t.slug}: {e}")
                failed.append(t.slug)
        return failed

    def remove(self, names):
        """Delete themes: files, wallpapers and profile. Built-ins only lose the profile."""
        known = set(self.store.slugs())
        unknown = [n for n in names if n not in known]
        if unknown:
            raise StoreError(f"unknown theme: {', '.join(unknown)}")
        with self.dms.autosave_paused():
            active = self.dms.active()
            original = self.dms.find_profile("original", "Original")
            for slug in names:
                prof = self.dms.find_profile(slug, theme.profile_name(slug))
                if prof:
                    if active == prof["slug"] and original and original["slug"] != active:
                        self.dms.apply_profile(original["slug"])  # leave it before deleting it
                        active = original["slug"]
                    self.dms.remove_profile(prof["slug"])
                if self.store.remove(slug):
                    self.log(f"removed: {slug}")
                else:
                    self.log(f"removed profile: {slug} (built-in files are managed by Nix; sync recreates it)")

    def hook(self, slug):
        """dmsProfiles apply command: point the wallpaper back at the whole theme folder.

        A profile carries one wallpaper copy (plus its thumbnail), which is all
        the carousel would list. dmsProfiles sets its own wallpaper *after* this
        command, so the change lands a moment later.
        """
        images = self.store.images(slug)
        if images:
            self.dms.set_wallpaper_later(images[0])
