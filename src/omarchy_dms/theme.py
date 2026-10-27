"""Omarchy colors.toml -> DMS custom theme folder (theme.json + Browse previews).

Pure: no DMS, no network. Omarchy has no Material roles, so the mapping is an
approximation. Community themes come in two shapes: the derived palette
(accent, selection, red, ...) and a plain ANSI one (color0..color15). Whatever is
missing is derived from background/foreground and the ANSI colors.
"""

import json
import pathlib
import string
import tomllib

REQUIRED = ("background", "foreground", "accent")
FONT = 'font-family="system-ui, sans-serif"'


class ThemeError(ValueError):
    pass


def _rgb(h):
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError as e:
        raise ThemeError(f"bad color {h!r}") from e


def _hexed(t):
    r, g, b = (round(v) for v in t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _mix(a, b, t):
    return _hexed(tuple(x * (1 - t) + y * t for x, y in zip(_rgb(a), _rgb(b), strict=True)))


def _luminance(h):
    r, g, b = (v / 255 for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def profile_name(slug):
    return string.capwords(slug.replace("-", " "))


def load_palette(path):
    try:
        palette = tomllib.loads(pathlib.Path(path).read_text())
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ThemeError(f"{path}: {e}") from e
    missing = [k for k in REQUIRED if k not in palette]
    if missing:
        raise ThemeError(f"{path}: missing {', '.join(missing)}")
    return palette


def mode_of(palette):
    return palette.get("mode") or ("light" if _luminance(palette["background"]) > 0.5 else "dark")


def convert(palette, slug):
    bg, fg, accent = palette["background"], palette["foreground"], palette["accent"]
    light = mode_of(palette) == "light"
    raise_to = "#000000" if light else "#ffffff"

    def pick(*keys, default):
        return next((palette[k] for k in keys if k in palette), default)

    dark_bg = pick("dark_background", default=_mix(bg, "#000000", 0.05 if light else 0.15))
    darker_bg = pick("darker_background", default=_mix(bg, "#000000", 0.1 if light else 0.3))
    lighter_bg = pick("lighter_background", default=_mix(bg, raise_to, 0.08))
    # selection_background in the ANSI shape is often a loud highlight, so not used.
    selection = pick("selection", default=_mix(bg, raise_to, 0.16))

    colors = {
        "primary": accent,
        "primaryText": bg,
        "primaryContainer": selection,
        "secondary": pick("magenta", "color5", default=accent),
        "surface": bg,
        "surfaceText": fg,
        "surfaceVariant": dark_bg if light else lighter_bg,
        "surfaceVariantText": fg,
        "surfaceTint": accent,
        "background": bg if light else dark_bg,
        "backgroundText": pick("bright_foreground", default=fg),
        "outline": pick("muted", "color8", default=_mix(fg, bg, 0.5)),
        "surfaceContainerLowest": bg if light else darker_bg,
        "surfaceContainerLow": bg if light else dark_bg,
        "surfaceContainer": dark_bg if light else lighter_bg,
        "surfaceContainerHigh": darker_bg if light else selection,
        "error": pick("red", "color1", default=accent),
        "warning": pick("yellow", "color3", default=accent),
        "info": pick("blue", "color4", default=accent),
    }
    return {
        "id": f"omarchy-{slug}",
        "name": f"Omarchy {profile_name(slug)}",
        "version": "1.0.0",
        "author": "Omarchy",
        "description": f"Omarchy {slug} palette",
        "dark": colors,
        "light": colors,
    }


def preview(theme, mode):
    c = theme["dark"]
    title = f"{theme['name']} ({mode})"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="280" height="240" viewBox="0 0 280 240">
  <rect width="280" height="240" fill="{c['background']}"/>
  <rect width="280" height="26" fill="{c['surface']}"/>
  <rect x="12" y="9" width="20" height="8" rx="4" fill="{c['primary']}"/>
  <circle cx="40" cy="13" r="3" fill="{c['surfaceVariantText']}"/>
  <circle cx="50" cy="13" r="3" fill="{c['surfaceVariantText']}"/>
  <text x="140" y="17" {FONT} font-size="10" font-weight="600" text-anchor="middle" fill="{c['primary']}">9:41</text>
  <circle cx="238" cy="13" r="4" fill="{c['info']}"/>
  <circle cx="252" cy="13" r="4" fill="{c['warning']}"/>
  <circle cx="266" cy="13" r="4" fill="{c['error']}"/>
  <rect x="14" y="38" width="252" height="190" rx="12" fill="{c['surface']}" stroke="{c['outline']}" stroke-opacity="0.5"/>
  <text x="28" y="61" {FONT} font-size="12.5" font-weight="600" fill="{c['surfaceText']}">{title}</text>
  <text x="28" y="77" {FONT} font-size="9.5" fill="{c['surfaceVariantText']}">Secondary text</text>
  <rect x="26" y="87" width="228" height="50" rx="8" fill="{c['surfaceContainerHigh']}"/>
  <text x="38" y="105" {FONT} font-size="10" font-weight="500" fill="{c['surfaceText']}">Nested card</text>
  <text x="38" y="120" {FONT} font-size="9" fill="{c['surfaceVariantText']}">Body text on an elevated surface</text>
  <rect x="26" y="145" width="228" height="22" rx="6" fill="{c['surface']}" stroke="{c['outline']}" stroke-opacity="0.4"/>
  <text x="38" y="160" {FONT} font-size="9" fill="{c['surfaceVariantText']}">Search</text>
  <rect x="26" y="175" width="78" height="22" rx="11" fill="{c['primary']}"/>
  <text x="65" y="190" {FONT} font-size="9.5" font-weight="600" text-anchor="middle" fill="{c['primaryText']}">Button</text>
  <rect x="112" y="175" width="70" height="22" rx="11" fill="{c['primary']}" fill-opacity="0.15"/>
  <text x="147" y="190" {FONT} font-size="9.5" font-weight="500" text-anchor="middle" fill="{c['primary']}">Accent</text>
  <rect x="190" y="175" width="64" height="22" rx="11" fill="{c['surfaceContainerHigh']}"/>
  <text x="222" y="190" {FONT} font-size="9.5" text-anchor="middle" fill="{c['surfaceText']}">Chip</text>
  <circle cx="34" cy="212" r="7" fill="{c['primary']}"/>
  <circle cx="54" cy="212" r="7" fill="{c['secondary']}"/>
  <circle cx="74" cy="212" r="7" fill="{c['error']}"/>
  <circle cx="94" cy="212" r="7" fill="{c['warning']}"/>
  <circle cx="114" cy="212" r="7" fill="{c['info']}"/>
</svg>
"""


def render(colors_toml, slug, outdir):
    """Write theme.json and the two Browse previews into OUTDIR; return the mode."""
    palette = load_palette(colors_toml)
    theme = convert(palette, slug)
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "theme.json").write_text(json.dumps(theme, indent=2) + "\n")
    for mode in ("dark", "light"):
        (out / f"preview-{mode}.svg").write_text(preview(theme, mode))
    return mode_of(palette)
