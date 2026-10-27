"""Theme folders and wallpapers on disk, and fetching community themes.

Built-in themes (Omarchy's own, deployed by Nix) are symlinks into the store and
read-only; community ones are real folders this module owns.
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

    def is_builtin(self, slug):
        return self.theme_json(slug).is_symlink() or self.wallpapers(slug).is_symlink()

    def source(self, slug):
        f = self.theme_dir(slug) / ".source"
        return f.read_text().strip() if f.is_file() else None

    def themes(self):
        return [Theme(s, self.is_builtin(s), self.source(s)) for s in self.slugs()]

    def images(self, slug):
        d = self.wallpapers(slug)
        return sorted(p for p in d.iterdir() if p.is_file()) if d.is_dir() else []

    def fetch(self, url, slug):
        """Clone URL and (re)write the theme folder and wallpapers; return the mode."""
        if not SLUG_RE.fullmatch(slug):
            raise StoreError(f"unusable theme name: {slug!r}")
        if self.is_builtin(slug):
            raise StoreError(f"{slug} is one of Omarchy's built-in themes")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            r = subprocess.run(
                ["git", "clone", "--quiet", "--depth", "1", "--", url, str(repo)],
                capture_output=True, text=True, check=False,
            )
            if r.returncode:
                raise StoreError(f"git clone {url}: {r.stderr.strip()}")
            colors = repo / "colors.toml"
            if not colors.is_file():
                raise StoreError(f"{url} has no colors.toml (alacritty-only themes are not supported)")
            mode = theme.render(colors, slug, self.theme_dir(slug))
            walls = self.wallpapers(slug)
            walls.mkdir(parents=True, exist_ok=True)
            backgrounds = repo / "backgrounds"
            for img in sorted(backgrounds.iterdir()) if backgrounds.is_dir() else []:
                if (
                    img.is_file() and not img.is_symlink()
                    and img.suffix.lower() in IMAGE_SUFFIXES
                    and img.stat().st_size > MIN_IMAGE_BYTES
                ):
                    shutil.copyfile(img, walls / img.name)
        # Remembered so `update` can fetch it again.
        (self.theme_dir(slug) / ".source").write_text(url + "\n")
        return mode

    def remove(self, slug):
        """Delete a community theme and its wallpapers; False for a built-in one."""
        if slug not in self.slugs():
            raise StoreError(f"unknown theme: {slug}")
        if self.is_builtin(slug):
            return False
        try:
            shutil.rmtree(self.theme_dir(slug))
            shutil.rmtree(self.wallpapers(slug), ignore_errors=True)
        except OSError as e:
            raise StoreError(f"cannot remove {slug}: {e}") from e
        return True
