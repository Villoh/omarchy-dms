"""Thin client for the DMS shell over `dms ipc`.

`runner` is the only thing that touches the process table, so a frontend or a
test can swap it. Calls the plugin finishes asynchronously (create, remove,
apply) are polled until the shell reports the result, instead of sleeping.
"""

import contextlib
import json
import subprocess
import time
from collections.abc import Callable

Runner = Callable[[list[str]], str]


class DmsError(RuntimeError):
    pass


def run_dms(args):
    try:
        p = subprocess.run(["dms", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        raise DmsError("dms not found in PATH") from e
    if p.returncode:
        raise DmsError(f"dms {' '.join(args)}: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout.strip()


class Dms:
    def __init__(self, runner: Runner = run_dms, sleep=time.sleep, attempts=60, interval=0.25,
                 spawn: Callable[..., object] = subprocess.Popen):
        self._run = runner
        self._sleep = sleep
        self.attempts = attempts
        self.interval = interval
        self._spawn = spawn

    def ipc(self, *args):
        return self._run(["ipc", "call", *args])

    def _json(self, *args):
        out = self.ipc(*args)
        try:
            return json.loads(out or "null")
        except json.JSONDecodeError as e:
            raise DmsError(f"dms ipc call {' '.join(args)}: not JSON: {out[:80]!r}") from e

    def _wait(self, what, ok):
        for _ in range(self.attempts):
            if ok():
                return
            self._sleep(self.interval)
        raise DmsError(f"timed out waiting for {what}")

    # -- reading
    def profiles(self):
        return self._json("profiles", "list") or []

    def find_profile(self, slug, name):
        return next((p for p in self.profiles() if p.get("slug") == slug or p.get("name") == name), None)

    def status(self):
        return self._json("profiles", "status") or {}

    def active(self):
        return self.status().get("active", "")

    def snapshot(self):
        return self._json("profiles", "snapshot") or {}

    # -- profiles
    def set_option(self, key, value):
        self.ipc("profiles", "setOption", key, value)

    @contextlib.contextmanager
    def autosave_paused(self):
        """Autosave would write each theme change into the previously active profile."""
        self.set_option("autosave", "false")
        try:
            yield
        finally:
            self.set_option("autosave", "true")

    def create_profile(self, name):
        self.ipc("profiles", "create", name)
        self._wait(f"profile {name!r}", lambda: any(p.get("name") == name for p in self.profiles()))

    def remove_profile(self, slug):
        self.ipc("profiles", "remove", slug)
        self._wait(f"profile {slug!r} to go", lambda: all(p.get("slug") != slug for p in self.profiles()))

    def apply_profile(self, slug):
        self.ipc("profiles", "apply", slug)

        def done():
            s = self.status()
            return s.get("active") == slug and not s.get("switching")

        self._wait(f"profile {slug!r} to apply", done)

    # -- the look itself
    def custom_theme(self, theme_json, theme_id):
        self.ipc("profiles", "customTheme", str(theme_json), theme_id, "default", "default", "default", "both")
        self._wait("theme", lambda: self.snapshot().get("settings", {}).get("customThemeFile") == str(theme_json))

    def set_mode(self, mode):
        self.ipc("theme", mode)
        self._wait(f"{mode} mode", lambda: self.snapshot().get("session", {}).get("isLightMode") == (mode == "light"))

    def set_wallpaper(self, path):
        out = self.ipc("wallpaper", "set", str(path))
        if out.startswith("ERROR"):
            raise DmsError(out)
        self._wait("wallpaper", lambda: self.snapshot().get("session", {}).get("wallpaperPath") == str(path))

    def set_wallpaper_later(self, path, delay=2):
        """Detached, so the caller (dmsProfiles' apply command) returns at once."""
        self._spawn(
            ["sh", "-c", 'sleep "$1"; exec dms ipc call wallpaper set "$2"', "_", str(delay), str(path)],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
