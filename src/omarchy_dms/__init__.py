"""Omarchy themes as DMS profiles.

Library first: `ops.Omarchy` is the API (no printing, no exiting, progress goes
to a `log` callback); `cli` is one thin frontend over it. Other frontends import
this package instead of shelling out to the CLI.
"""

from importlib.metadata import PackageNotFoundError, version

from .dms import Dms, DmsError
from .ops import Omarchy, Row, store_repos
from .store import Store, StoreError, Theme, resolve_repo
from .theme import ThemeError

try:
    __version__ = version("omarchy-dms")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "unknown"

__all__ = [
    "__version__",
    "Dms",
    "DmsError",
    "Omarchy",
    "Row",
    "Store",
    "StoreError",
    "Theme",
    "ThemeError",
    "resolve_repo",
    "store_repos",
]
