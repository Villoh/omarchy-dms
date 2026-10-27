"""Theme folders and wallpapers on disk, and fetching themes.

A theme folder is either one this module wrote (community themes carry a
`.source` file, Omarchy's own a `.builtin` one) or one deployed by something
else as symlinks into a read-only location (for example Nix), which is only ever
read.
"""

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import theme

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MIN_IMAGE_BYTES = 2048  # drops the ~700-byte placeholders
SLUG_RE = re.compile(r"[a-z0-9_][a-z0-9._+-]*")
SHORTHAND_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


class StoreError(RuntimeError):
    pass


def clone(url, dest, sparse=()):
    """Shallow clone; with SPARSE (gitignore-style patterns) only those paths are downloaded."""

    def git(*args):
        r = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
        if r.returncode:
            raise StoreError(f"git clone {url}: {r.stderr.strip()}")

    if not sparse:
        git("clone", "--quiet", "--depth", "1", "--", url, str(dest))
        return
    git("clone", "--quiet", "--depth", "1", "--filter=blob:none", "--no-checkout", "--", url, str(dest))
    git("-C", str(dest), "sparse-checkout", "set", "--no-cone", *sparse)
    git("-C", str(dest), "checkout", "--quiet", "HEAD")


@dataclass(frozen=True)
class Theme:
    slug: str
    builtin: bool
    source: str | None


def resolve_repo(arg):
    """owner/repo or a git URL -> (url, slug). Same naming as omarchy-theme-install."""
    arg = arg.strip()
    if arg.startswith(("https://", "ssh://", "git@")):
        url = arg
    elif SHORTHAND_RE.fullmatch(arg):
        url = f"https://github.com/{arg}"
    else:
        raise StoreError("expected owner/repo or a git URL")
    name = arg.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1].rsplit(":", 1)[-1].lower()
    slug = name.removeprefix("omarchy-").removesuffix("-theme")
    if not SLUG_RE.fullmatch(slug):
        raise StoreError(f"unusable theme name: {slug!r}")
    return url, slug


class Store:
    def __init__(self, themes_dir, wall_dir):
        self.themes_dir = Path(themes_dir)
        self.wall_dir = Path(wall_dir)

    def theme_dir(self, slug):
        return self.themes_dir / f"omarchy-{slug}"

    def theme_json(self, slug):
        return self.theme_dir(slug) / "theme.json"

    def wallpapers(self, slug):
        return self.wall_dir / slug

    def slugs(self):
        # .source counts too: a community theme whose theme.json went missing can still be updated.
        return sorted(
            d.name.removeprefix("omarchy-")
            for d in self.themes_dir.glob("omarchy-*")
            if (d / "theme.json").is_file() or (d / ".source").is_file()
        )

    def is_readonly(self, slug):
        """Deployed as symlinks by something else (for example Nix): never written."""
        return self.theme_json(slug).is_symlink() or self.wallpapers(slug).is_symlink()

    def is_builtin(self, slug):
        """One of Omarchy's own themes, however it got here."""
        return self.is_readonly(slug) or (self.theme_dir(slug) / ".builtin").is_file()

    def source(self, slug):
        f = self.theme_dir(slug) / ".source"
        return f.read_text().strip() if f.is_file() else None

    def themes(self):
        return [Theme(s, self.is_builtin(s), self.source(s)) for s in self.slugs()]

    def images(self, slug):
        d = self.wallpapers(slug)
        return sorted(p for p in d.iterdir() if p.is_file()) if d.is_dir() else []

    def _write(self, slug, src):
        """Render SRC (a theme directory: colors.toml, backgrounds/) into the DMS folders."""
        mode = theme.render(src / "colors.toml", slug, self.theme_dir(slug))
        walls = self.wallpapers(slug)
        walls.mkdir(parents=True, exist_ok=True)
        backgrounds = src / "backgrounds"
        for img in sorted(backgrounds.iterdir()) if backgrounds.is_dir() else []:
            if (
                img.is_file()
                and not img.is_symlink()
                and img.suffix.lower() in IMAGE_SUFFIXES
                and img.stat().st_size > MIN_IMAGE_BYTES
            ):
                shutil.copyfile(img, walls / img.name)
        return mode

    def fetch(self, url, slug):
        """Clone a community theme and (re)write its folder and wallpapers; return the mode."""
        if not SLUG_RE.fullmatch(slug):
            raise StoreError(f"unusable theme name: {slug!r}")
        if self.is_builtin(slug):
            raise StoreError(f"{slug} is one of Omarchy's own themes (use sync)")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            clone(url, repo)
            if not (repo / "colors.toml").is_file():
                raise StoreError(f"{url} has no colors.toml (alacritty-only themes are not supported)")
            mode = self._write(slug, repo)
        # Remembered so `update` can fetch it again.
        (self.theme_dir(slug) / ".source").write_text(url + "\n")
        return mode

    def install_builtin(self, slug, src):
        """Write one of Omarchy's own themes from its directory in a checkout."""
        if self.is_readonly(slug):
            raise StoreError(f"{slug} is deployed read-only; it cannot be rewritten")
        mode = self._write(slug, Path(src))
        (self.theme_dir(slug) / ".builtin").write_text("")
        return mode

    def remove(self, slug):
        """Delete a theme and its wallpapers; False if it is deployed read-only."""
        if slug not in self.slugs():
            raise StoreError(f"unknown theme: {slug}")
        if self.is_readonly(slug):
            return False
        try:
            shutil.rmtree(self.theme_dir(slug))
            shutil.rmtree(self.wallpapers(slug), ignore_errors=True)
        except OSError as e:
            raise StoreError(f"cannot remove {slug}: {e}") from e
        return True
