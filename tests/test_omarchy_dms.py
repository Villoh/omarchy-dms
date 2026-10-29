"""Run with: python3 -m unittest discover -s tests (from this directory)."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omarchy_dms import theme
from omarchy_dms.dms import Dms, DmsError
from omarchy_dms.ops import Omarchy
from omarchy_dms.store import Store, StoreError, resolve_repo
from omarchy_dms.theme import ThemeError

DARK = 'mode = "dark"\naccent = "#7aa2f7"\nbackground = "#1a1b26"\nforeground = "#a9b1d6"\n'
LIGHT = 'mode = "light"\naccent = "#1e66f5"\nbackground = "#eff1f5"\nforeground = "#4c4f69"\n'
ANSI = (
    'accent = "#8be9fd"\nbackground = "#282a36"\nforeground = "#f8f8f2"\n'
    'color1 = "#ff5555"\ncolor3 = "#f1fa8c"\ncolor4 = "#bd93f9"\ncolor5 = "#ff79c6"\ncolor8 = "#6272a4"\n'
)


class FakeShell:
    """A stateful stand-in for `dms ipc`; profiles appear only after `delay` polls."""

    def __init__(self, delay=2, profiles=()):
        self.state = {"customThemeFile": "", "isLightMode": False, "wallpaperPath": ""}
        self.profiles = [{"slug": s, "name": s.title()} for s in profiles]
        self.active = ""
        self.options = {}
        self.calls = []
        self.delay = delay
        self.pending = []  # (polls_left, effect)

    def _tick(self):
        keep = []
        for left, effect in self.pending:
            if left <= 1:
                effect()
            else:
                keep.append((left - 1, effect))
        self.pending = keep

    def __call__(self, argv):
        assert argv[:2] == ["ipc", "call"], argv
        a = argv[2:]
        self.calls.append(a)
        self._tick()
        match a:
            case ["profiles", "list"]:
                return json.dumps(self.profiles)
            case ["profiles", "status"]:
                return json.dumps({"active": self.active, "switching": bool(self.pending)})
            case ["profiles", "snapshot"]:
                return json.dumps(
                    {
                        "settings": {"customThemeFile": self.state["customThemeFile"]},
                        "session": {k: self.state[k] for k in ("isLightMode", "wallpaperPath")},
                    }
                )
            case ["profiles", "folder", slug, path]:
                if getattr(self, "folder_missing", False):
                    return "Function not found."
                if not path.startswith("/"):
                    return "the folder must be an absolute path"
                if slug not in [p["slug"] for p in self.profiles]:
                    return f"no profile {slug}"
                for p in self.profiles:
                    if p["slug"] == slug:
                        self.pending.append((self.delay, lambda p=p, path=path: p.update(wallpaperFolder=path)))
                return "started"
            case ["profiles", "setOption", k, v]:
                self.options[k] = v
            case ["profiles", "create", name]:
                slug = name.lower().replace(" ", "-")

                def add(slug=slug, name=name):
                    self.profiles.append({"slug": slug, "name": name})
                    self.active = slug

                self.pending.append((self.delay, add))
            case ["profiles", "remove", slug]:

                def drop(slug=slug):
                    self.profiles = [p for p in self.profiles if p["slug"] != slug]

                self.pending.append((self.delay, drop))
            case ["profiles", "apply", slug]:

                def go(slug=slug):
                    self.active = slug

                self.pending.append((self.delay, go))
            case ["profiles", "customTheme", f, *_]:
                self.pending.append((self.delay, lambda f=f: self.state.update(customThemeFile=f)))
            case ["theme", mode]:
                self.pending.append((self.delay, lambda m=mode: self.state.update(isLightMode=m == "light")))
            case ["wallpaper", "set", p]:
                self.pending.append((self.delay, lambda p=p: self.state.update(wallpaperPath=p)))
                return f"SUCCESS: Wallpaper set to {p}"
            case _:
                raise AssertionError(a)
        return "ok"


class Env:
    def __init__(self, test, profiles=(), builtin=("nord",)):
        tmp = Path(tempfile.mkdtemp())
        test.addCleanup(lambda: subprocess.run(["rm", "-rf", str(tmp)], check=False))
        self.tmp = tmp
        self.builtin_dir = tmp / "omarchy-themes"
        for slug in builtin:
            (self.builtin_dir / slug).mkdir(parents=True)
            (self.builtin_dir / slug / "colors.toml").write_text(LIGHT if slug == "white" else DARK)
        self.store = Store(tmp / "themes", tmp / "wall")
        self.store.themes_dir.mkdir()
        self.store.wall_dir.mkdir()
        self.shell = FakeShell(profiles=profiles)
        self.logs = []
        self.omarchy = Omarchy(
            Dms(self.shell, sleep=lambda s: None),
            self.store,
            self.builtin_dir,
            self.logs.append,
            0,
            lambda s: None,
        )

    def deploy_builtin(self, slug):
        """What Home Manager does: real theme folder, symlinked files and wallpapers."""
        store_dir = self.tmp / "nix-store" / slug
        (store_dir / "walls").mkdir(parents=True)
        (store_dir / "walls" / "1.webp").write_bytes(b"x" * 5000)
        theme.render(self.builtin_dir / slug / "colors.toml", slug, store_dir / "theme")
        d = self.store.theme_dir(slug)
        d.mkdir()
        (d / "theme.json").symlink_to(store_dir / "theme" / "theme.json")
        self.store.wallpapers(slug).symlink_to(store_dir / "walls")

    def community_repo(self, colors=ANSI, images=("1-a.jpg", "2-b.png")):
        repo = self.tmp / "remote" / "omarchy-dracula-theme"
        (repo / "backgrounds").mkdir(parents=True)
        (repo / "colors.toml").write_text(colors)
        for i in images:
            (repo / "backgrounds" / i).write_bytes(b"x" * 5000)
        (repo / "backgrounds" / "tiny.png").write_bytes(b"x")
        (repo / "backgrounds" / "intro.mp4").write_bytes(b"x" * 5000)
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        for cmd in (["init", "-q"], ["add", "."], ["-c", "commit.gpgsign=false", "commit", "-q", "-m", "x"]):
            subprocess.run(["git", "-C", str(repo), *cmd], check=True, env=env)
        return f"file://{repo}"


class ThemeTests(unittest.TestCase):
    def test_modes_and_missing_keys(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.toml"
            p.write_text(ANSI)
            pal = theme.load_palette(p)
            self.assertEqual(theme.mode_of(pal), "dark")  # derived from the background
            t = theme.convert(pal, "dracula")
            self.assertEqual(t["dark"]["error"], "#ff5555")  # ANSI fallback
            self.assertEqual(t["name"], "Omarchy Dracula")
            p.write_text('accent = "#fff"\n')
            with self.assertRaises(ThemeError):
                theme.load_palette(p)
            p.write_text('accent = "#fff"\nbackground = "zz"\nforeground = "#fff"\n')
            with self.assertRaises(ThemeError):
                theme.convert(theme.load_palette(p), "x")

    def test_light_palette(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.toml"
            p.write_text(LIGHT)
            self.assertEqual(theme.mode_of(theme.load_palette(p)), "light")


class CliTests(unittest.TestCase):
    def test_version_flag(self):
        import io
        from contextlib import redirect_stdout

        import omarchy_dms
        from omarchy_dms.cli import main

        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), f"omarchy-dms {omarchy_dms.__version__}")
        self.assertRegex(omarchy_dms.__version__, r"^(\d+\.\d+\.\d+.*|unknown)$")


class RepoTests(unittest.TestCase):
    def test_resolve(self):
        self.assertEqual(
            resolve_repo("catlee/omarchy-dracula-theme"), ("https://github.com/catlee/omarchy-dracula-theme", "dracula")
        )
        self.assertEqual(resolve_repo("https://github.com/r-bart/omarchy-periphery-theme.git")[1], "periphery")
        self.assertEqual(resolve_repo("git@github.com:a/Omarchy-Foo-Theme.git")[1], "foo")
        for bad in ("gruvbox", "../x/y", "a/b/c", "https://x/.."):
            with self.assertRaises(StoreError, msg=bad):
                resolve_repo(bad)


class OpsTests(unittest.TestCase):
    def test_sync_creates_original_then_profiles_and_is_idempotent(self):
        e = Env(self, builtin=("nord", "white"))
        for s in ("nord", "white"):
            e.deploy_builtin(s)
        e.omarchy.sync()
        self.assertEqual([p["slug"] for p in e.shell.profiles], ["original", "nord", "white"])
        self.assertEqual(e.shell.state["isLightMode"], True)  # white was last
        self.assertEqual(e.shell.options, {"autosave": "true"})
        e.logs.clear()
        e.omarchy.sync()
        self.assertEqual(e.logs, ["skip: Nord", "skip: White"])

    def test_sync_force_and_names(self):
        e = Env(self, builtin=("nord", "white"))
        for s in ("nord", "white"):
            e.deploy_builtin(s)
        e.omarchy.sync()
        e.logs.clear()
        e.omarchy.sync(["nord"], force=True)
        self.assertEqual(e.logs, ["create: Nord"])
        with self.assertRaises(StoreError):
            e.omarchy.sync(["nope"])

    def test_sync_writes_missing_theme_files_from_a_plain_checkout(self):
        """No Nix: the theme folders and wallpapers do not exist yet and sync creates them."""
        e = Env(self, builtin=("nord",))
        (e.builtin_dir / "nord" / "backgrounds").mkdir()
        (e.builtin_dir / "nord" / "backgrounds" / "1-a.jpg").write_bytes(b"x" * 5000)
        (e.builtin_dir / "nord" / "backgrounds" / "tiny.png").write_bytes(b"x")
        e.omarchy.sync()
        self.assertTrue(e.store.theme_json("nord").is_file())
        self.assertFalse(e.store.theme_json("nord").is_symlink())
        self.assertEqual([p.name for p in e.store.images("nord")], ["1-a.jpg"])
        self.assertEqual([r.origin for r in e.omarchy.installed()], ["built-in"])
        self.assertEqual([p["slug"] for p in e.shell.profiles], ["original", "nord"])
        self.assertEqual(e.shell.state["wallpaperPath"], str(e.store.images("nord")[0]))
        self.assertEqual(e.shell.options.get("autosave"), "true")

    def test_sync_leaves_existing_files_unless_forced_and_never_rewrites_readonly(self):
        e = Env(self, builtin=("nord", "white"))
        e.deploy_builtin("nord")  # deployed read-only, like Nix does
        before = e.store.theme_json("nord").resolve()
        e.omarchy.sync(["nord"], force=True)
        self.assertEqual(e.store.theme_json("nord").resolve(), before)
        self.assertTrue(e.store.theme_json("nord").is_symlink())
        e.omarchy.sync(["white"])
        marker = e.store.theme_dir("white") / "theme.json"
        marker.write_text("edited")
        e.omarchy.sync(["white"], force=True)
        self.assertNotEqual(marker.read_text(), "edited")  # forced: rewritten

    def test_sync_without_a_checkout_clones_only_what_it_needs(self):
        e = Env(self, builtin=())
        remote = e.tmp / "remote-omarchy"
        for slug in ("nord", "white"):
            d = remote / "themes" / slug
            (d / "backgrounds" / "intros").mkdir(parents=True)
            (d / "colors.toml").write_text(LIGHT if slug == "white" else DARK)
            (d / "backgrounds" / "1.jpg").write_bytes(b"x" * 5000)
            (d / "backgrounds" / "intros" / "intro.png").write_bytes(b"x" * 5000)
            (d / "preview.png").write_bytes(b"x" * 5000)
        git_env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        for cmd in (["init", "-q"], ["add", "."], ["-c", "commit.gpgsign=false", "commit", "-q", "-m", "x"]):
            subprocess.run(["git", "-C", str(remote), *cmd], check=True, env=git_env)
        e.omarchy = Omarchy(
            e.omarchy.dms,
            e.store,
            None,
            e.logs.append,
            0,
            lambda s: None,
            omarchy_repo=f"file://{remote}",
        )
        e.omarchy.sync(["white"])
        self.assertEqual([p["slug"] for p in e.shell.profiles], ["original", "white"])
        self.assertTrue(e.store.theme_json("white").is_file())
        self.assertFalse(e.store.theme_dir("nord").exists())  # only the one asked for
        self.assertEqual([p.name for p in e.store.images("white")], ["1.jpg"])  # no intros
        self.assertEqual(e.shell.state["isLightMode"], True)

    def test_sync_rejects_a_missing_directory(self):
        e = Env(self)
        e.omarchy.builtin_dir = e.tmp / "nope"
        with self.assertRaises(StoreError):
            e.omarchy.sync()

    def test_remove_and_update_for_themes_written_by_sync(self):
        e = Env(self, builtin=("nord",))
        e.omarchy.sync()
        e.logs.clear()
        e.omarchy.update(["nord"])
        self.assertEqual(e.logs, ["nord is one of Omarchy's own themes: use sync --force"])
        with self.assertRaises(StoreError):  # a community repo cannot take over the name
            e.store.fetch("https://example.invalid/x", "nord")
        e.omarchy.remove(["nord"])
        self.assertFalse(e.store.theme_dir("nord").exists())  # not read-only: really deleted
        self.assertEqual([p["slug"] for p in e.shell.profiles], ["original"])

    def test_install_update_remove_community(self):
        e = Env(self, profiles=("original",))
        url = e.community_repo()
        # file:// URLs are not owner/repo, so drive the store directly like install does
        mode = e.store.fetch(url, "dracula")
        self.assertEqual(mode, "dark")
        self.assertEqual([p.name for p in e.store.images("dracula")], ["1-a.jpg", "2-b.png"])  # no tiny, no mp4
        self.assertEqual(e.store.source("dracula"), url)
        self.assertEqual([r.origin for r in e.omarchy.installed()], [url])
        e.omarchy._make("dracula", mode, True)
        self.assertEqual(e.shell.state["wallpaperPath"], str(e.store.images("dracula")[0]))
        self.assertTrue(e.omarchy.installed()[0].profile)

        (e.store.theme_dir("dracula") / "theme.json").unlink()
        self.assertEqual(e.omarchy.update(), [])
        self.assertTrue(e.store.theme_json("dracula").is_file())  # regenerated

        e.shell.active = "dracula"
        e.omarchy.remove(["dracula"])
        self.assertEqual(e.shell.active, "original")  # left before deleting
        self.assertEqual([p["slug"] for p in e.shell.profiles], ["original"])
        self.assertFalse(e.store.theme_dir("dracula").exists())
        self.assertFalse(e.store.wallpapers("dracula").exists())

    def test_remove_and_update_accept_the_repo_they_were_installed_from(self):
        e = Env(self, profiles=("original",))
        e.store.fetch(e.community_repo(), "dracula")
        self.assertEqual(e.omarchy.update(["someone/omarchy-dracula-theme"]), [])
        e.omarchy.remove(["someone/omarchy-dracula-theme"])
        self.assertFalse(e.store.theme_dir("dracula").exists())

    def test_available_sorts_by_slug_and_marks_installed(self):
        e = Env(self, profiles=("original",))
        e.store.fetch(e.community_repo(), "dracula")
        repos = ["b/omarchy-zed-theme", "a/omarchy-dracula-theme", "c/bad name"]
        with mock.patch("omarchy_dms.ops.store_repos", return_value=repos):
            self.assertEqual(
                e.omarchy.available(),
                [("dracula", "a/omarchy-dracula-theme", True), ("zed", "b/omarchy-zed-theme", False)],
            )
            self.assertEqual(e.omarchy.available("ZED"), [("zed", "b/omarchy-zed-theme", False)])  # filter on slug/repo
            self.assertEqual(e.omarchy.available("a/"), [("dracula", "a/omarchy-dracula-theme", True)])
            self.assertEqual(e.omarchy.available(owner="B"), [("zed", "b/omarchy-zed-theme", False)])
            self.assertEqual(e.omarchy.available(only_new=True), [("zed", "b/omarchy-zed-theme", False)])

    def test_update_reports_failures_and_continues(self):
        e = Env(self)
        good = e.community_repo()
        e.store.fetch(good, "dracula")
        broken = e.store.theme_dir("broken")
        broken.mkdir()
        (broken / "theme.json").write_text("{}")
        (broken / ".source").write_text("file:///does/not/exist\n")
        failed = e.omarchy.update()
        self.assertEqual(failed, ["broken"])
        self.assertIn("update: dracula", " ".join(e.logs))
        e.logs.clear()
        e.omarchy.update(["nord"])
        self.assertEqual(e.logs, ["not updatable (no .source): nord"])

    def test_update_pins_the_folder_of_an_existing_profile(self):
        e = Env(self, profiles=("dracula",))
        e.store.fetch(e.community_repo(), "dracula")
        self.assertEqual(e.omarchy.update(), [])
        prof = e.omarchy.dms.find_profile("dracula", "")
        self.assertEqual(prof["wallpaperFolder"], str(e.store.wallpapers("dracula")))

    def test_fetch_rejects_alacritty_only_and_builtin(self):
        e = Env(self)
        url = e.community_repo()
        e.deploy_builtin("nord")
        with self.assertRaises(StoreError):
            e.store.fetch(url, "nord")
        repo = Path(url.removeprefix("file://"))
        (repo / "colors.toml").unlink()
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@t",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-qam",
                "x",
            ],
            check=True,
        )
        with self.assertRaises(StoreError):
            e.store.fetch(url, "other")

    def test_remove_builtin_only_drops_profile_and_validates_names(self):
        e = Env(self, profiles=("original", "nord"))
        e.deploy_builtin("nord")
        e.shell.active = "nord"
        e.omarchy.remove(["nord"])
        self.assertEqual([p["slug"] for p in e.shell.profiles], ["original"])
        self.assertTrue(e.store.theme_json("nord").is_symlink())  # untouched
        self.assertTrue(e.store.wallpapers("nord").is_symlink())
        for bad in ("../x", "nope"):
            with self.assertRaises(StoreError):
                e.omarchy.remove([bad])

    def test_sync_pins_the_wallpaper_folder_also_on_existing_profiles(self):
        e = Env(self, builtin=("nord", "white"))
        for slug in ("nord", "white"):
            e.deploy_builtin(slug)
        e.omarchy.sync()
        for slug in ("nord", "white"):
            prof = e.omarchy.dms.find_profile(slug, "")
            self.assertEqual(prof["wallpaperFolder"], str(e.store.wallpapers(slug)))
        e.shell.profiles[1].pop("wallpaperFolder")  # a profile made before this existed
        e.shell.calls.clear()
        e.omarchy.sync()
        self.assertEqual(
            [c for c in e.shell.calls if c[1] == "folder"],
            [["profiles", "folder", "nord", str(e.store.wallpapers("nord"))]],
        )

    def test_old_dmsprofiles_without_folder_command_warns_once_and_goes_on(self):
        e = Env(self, builtin=("nord", "white"))
        for slug in ("nord", "white"):
            e.deploy_builtin(slug)
        e.shell.folder_missing = True
        e.omarchy.sync()
        self.assertEqual([p["slug"] for p in e.shell.profiles], ["original", "nord", "white"])
        self.assertEqual(len([m for m in e.logs if m.startswith("warning:")]), 1)

    def test_a_folder_set_by_hand_is_kept(self):
        e = Env(self, builtin=("nord",))
        e.deploy_builtin("nord")
        e.omarchy.sync()
        e.shell.profiles[1]["wallpaperFolder"] = "/mine/"
        e.omarchy.sync()
        self.assertEqual(e.shell.profiles[1]["wallpaperFolder"], "/mine/")

    def test_update_survives_dms_failing(self):
        e = Env(self)
        e.store.fetch(e.community_repo(), "dracula")
        e.omarchy.dms.profiles = lambda: (_ for _ in ()).throw(DmsError("no dms"))
        self.assertEqual(e.omarchy.update(), [])
        self.assertTrue(any(m.startswith("warning: dracula") for m in e.logs))

    def test_timeout_when_shell_never_settles(self):
        e = Env(self)
        e.shell.delay = 10**6
        with self.assertRaises(DmsError):
            Dms(e.shell, sleep=lambda s: None, attempts=3).create_profile("X")


if __name__ == "__main__":
    unittest.main()
