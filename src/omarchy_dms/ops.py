"""What omarchy-dms does, as an API: sync, install, update, remove, installed.

No printing and no exiting: progress goes to `log`, problems are exceptions
(DmsError, StoreError, ThemeError), results are returned.
"""

import re
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import theme
from .dms import Dms, DmsError, FolderUnsupported
from .store import Store, StoreError, clone, resolve_repo

STORE_URL = "https://omarchy.org/themes/"
OMARCHY_REPO = "https://github.com/basecamp/omarchy"
# Only the colors and the still wallpapers: the repository also holds intro videos.
OWN_THEMES_SPARSE = ("/themes/*/colors.toml", "/themes/*/backgrounds/*", "!/themes/*/backgrounds/intros/")
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
        log: Callable[[str], None] = print,
        settle: float = 1.0,
        sleep=time.sleep,
        omarchy_repo: str = OMARCHY_REPO,
    ):
        self.dms = dms
        self.store = store
        self.builtin_dir = Path(builtin_dir) if builtin_dir else None
        self.log = log
        self.settle = settle
        self._sleep = sleep
        self.omarchy_repo = omarchy_repo
        self._folders = True  # False once dmsProfiles turned out not to have `profiles folder`

    # -- internals
    @contextmanager
    def _session(self):
        """Autosave off, and a way back (Original)."""
        with self.dms.autosave_paused():
            if not self.dms.find_profile("original", "Original"):
                self.log("create: Original")
                self.dms.create_profile("Original")
            yield

    @contextmanager
    def _own_themes(self):
        """Omarchy's themes/ directory: the one given, or a fresh partial clone."""
        if self.builtin_dir:
            if not self.builtin_dir.is_dir():
                raise StoreError(f"not a directory: {self.builtin_dir}")
            yield self.builtin_dir
            return
        self.log(f"fetching Omarchy's themes from {self.omarchy_repo}")
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "omarchy"
            clone(self.omarchy_repo, checkout, OWN_THEMES_SPARSE)
            yield checkout / "themes"

    def _ensure_files(self, slug, src, force):
        """Theme folder and wallpapers for one of Omarchy's themes, unless deployed read-only."""
        if self.store.is_readonly(slug):
            return
        if force or not self.store.theme_json(slug).is_file():
            self.store.install_builtin(slug, src)

    def _make(self, slug, mode, force):
        name = theme.profile_name(slug)
        existing = self.dms.find_profile(slug, name)
        if existing:
            if not force:
                self.log(f"skip: {name}")
                self._pin_folder(existing, slug, log=True)
                return
            self.dms.remove_profile(existing["slug"])
        if not self.store.theme_json(slug).is_file():
            raise StoreError(f"{slug}: theme files are missing (run sync or install)")
        self.dms.custom_theme(self.store.theme_json(slug), f"omarchy-{slug}")
        self.dms.set_mode(mode)
        images = self.store.images(slug)
        if images:
            self.dms.set_wallpaper(images[0])
        self._sleep(self.settle)
        self.log(f"create: {name}")
        self.dms.create_profile(name)
        self._pin_folder(self.dms.find_profile(slug, name), slug)

    def _pin_folder(self, prof, slug, log=False):
        """The picker of dmsProfiles opens on the theme's wallpapers, whatever the current one is.

        A folder set by hand is kept. With a dmsProfiles that cannot store it, warn once.
        """
        if not self._folders or prof.get("wallpaperFolder") or not self.store.images(slug):
            return
        if log:
            self.log(f"folder: {prof.get('name', slug)}")
        try:
            self.dms.set_wallpaper_folder(prof["slug"], str(self.store.wallpapers(slug)))
        except FolderUnsupported as e:
            self._folders = False
            self.log(f"warning: {e}")

    # -- operations
    def installed(self):
        names = {p.get("slug") for p in self.dms.profiles()} | {p.get("name") for p in self.dms.profiles()}
        return [
            Row(
                t.slug,
                t.slug in names or theme.profile_name(t.slug) in names,
                "built-in" if t.builtin else (t.source or ""),
            )
            for t in self.store.themes()
        ]

    def sync(self, names=(), force=False):
        """Profiles for Omarchy's own themes (all, or the ones named).

        Themes come from `builtin_dir` if given, otherwise from a partial clone of
        the Omarchy repository. Missing theme folders and wallpapers are written;
        with `force`, existing ones are rewritten too (unless deployed read-only).
        """
        with self._own_themes() as root:
            available = {p.parent.name: p.parent for p in sorted(root.glob("*/colors.toml"))}
            unknown = [n for n in names if n not in available]
            if unknown:
                raise StoreError(f"not an Omarchy theme: {', '.join(unknown)}")
            with self._session():
                for slug, src in available.items():
                    if not names or slug in names:
                        self._ensure_files(slug, src, force)
                        self._make(slug, theme.mode_of(theme.load_palette(src / "colors.toml")), force)

    def install(self, arg):
        """Install a community theme (owner/repo or git URL); returns its slug."""
        url, slug = resolve_repo(arg)
        mode = self.store.fetch(url, slug)
        with self._session():
            self._make(slug, mode, force=True)  # reinstalling refreshes the profile
        return slug

    def update(self, names=()):
        """Refetch installed community themes; returns the slugs that failed.

        Profiles are left alone, as they point at theme.json by path and the colors
        follow (`install` again to also refresh a profile's own wallpaper copy), except
        for their wallpaper folder, which is set if missing.
        """
        names = [self.slug(n) for n in names]
        by_slug = {t.slug: t for t in self.store.themes()}
        for n in names:
            if n in by_slug and by_slug[n].builtin:
                self.log(f"{n} is one of Omarchy's own themes: use sync --force")
            elif n not in by_slug or not by_slug[n].source:
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
                continue
            try:  # DMS is not needed to update, only to also set the wallpaper folder
                prof = self.dms.find_profile(t.slug, theme.profile_name(t.slug))
                if prof:
                    self._pin_folder(prof, t.slug, log=True)
            except DmsError as e:
                self.log(f"warning: {t.slug}: wallpaper folder not set: {e}")
        return failed

    def available(self, query="", owner="", only_new=False):
        """The store's themes as (slug, owner/repo, installed), sorted by slug.

        `query` must be in the slug or repo, `owner` must be the repo's owner, `only_new` drops
        the ones you already have.
        """
        have = set(self.store.slugs())
        rows = []
        for repo in store_repos():
            try:
                slug = resolve_repo(repo)[1]
            except StoreError:
                continue  # a name that could never be installed
            if (
                query.lower() in f"{slug} {repo}".lower()
                and (not owner or repo.split("/")[0].lower() == owner.lower())
                and not (only_new and slug in have)
            ):
                rows.append((slug, repo, slug in have))
        return sorted(rows)

    def slug(self, name):
        """A theme slug for `name`, which may also be the owner/repo or URL it was installed from."""
        if name in self.store.slugs():
            return name
        try:
            return resolve_repo(name)[1]
        except StoreError:
            return name

    def remove(self, names):
        """Delete themes: files, wallpapers and profile. Built-ins only lose the profile."""
        names = [self.slug(n) for n in names]
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
                    self.log(f"removed profile: {slug} (its files are read-only here; sync recreates the profile)")
