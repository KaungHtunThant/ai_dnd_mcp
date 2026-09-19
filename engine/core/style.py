"""Art styles.

Every part in the game is drawn from the same procedural grids, so a style is not a
different set of art - it is a transform applied to the final colour of every pixel,
plus how outlines and auto-shading behave. That means one choice restyles the whole
game (sprites, portraits, tiles, backdrops, item icons, the lot) with no new assets.

A style is picked in the New Game wizard before anything is generated, stored on the
theme as theme.json["style"], and optionally overridden per campaign.

    saturation  multiplier on colour saturation (0 = greyscale)
    lightness   additive shift, -1..1
    contrast    multiplier on the depth of the automatic :d / :l shading (0 = flat)
    outline     "dark" (the outline slot as authored) | "none" | "light" | "#hex"
    ramp        optional list of hex; every colour is quantised to the nearest step by
                luminance, which is what makes sepia / Game Boy read as one palette
"""
from __future__ import annotations
import colorsys

DEFAULT = "classic"

STYLES = {
    "classic": {
        "name": "Classic", "blurb": "Full colour with soft shading and a dark outline. The default look.",
        "saturation": 1.0, "lightness": 0.0, "contrast": 1.0, "outline": "dark", "ramp": None,
    },
    "flat": {
        "name": "Flat", "blurb": "Clean blocks of solid colour, no shading. Modern and graphic.",
        "saturation": 1.05, "lightness": 0.02, "contrast": 0.0, "outline": "dark", "ramp": None,
    },
    "neon": {
        "name": "Neon", "blurb": "Saturated and electric, deep shadows. Made for rain and signage.",
        "saturation": 1.5, "lightness": 0.04, "contrast": 1.3, "outline": "dark", "ramp": None,
    },
    "noir": {
        "name": "Noir", "blurb": "Almost colourless, hard contrast. Everything looks like a bad decision.",
        "saturation": 0.1, "lightness": -0.02, "contrast": 1.55, "outline": "dark", "ramp": None,
    },
    "pastel": {
        "name": "Pastel", "blurb": "Washed, gentle colour with a soft outline. Storybook.",
        "saturation": 0.5, "lightness": 0.2, "contrast": 0.6, "outline": "#7b7391", "ramp": None,
    },
    "sepia": {
        "name": "Sepia", "blurb": "Old print. One warm brown palette from black to paper.",
        "saturation": 0.0, "lightness": 0.0, "contrast": 1.15, "outline": "dark",
        "ramp": ["#1c1209", "#3d2a17", "#6b4a29", "#9c7549", "#c7a276", "#e8d6b5", "#f6eedd"],
    },
    "gameboy": {
        "name": "Game Boy", "blurb": "Four shades of green on a dot-matrix screen. 1989 forever.",
        "saturation": 0.0, "lightness": 0.0, "contrast": 1.6, "outline": "dark",
        "ramp": ["#0f380f", "#306230", "#8bac0f", "#9bbc0f"],
    },
    "ink": {
        "name": "Ink Wash", "blurb": "Muted paper tones with heavy black linework. Graphic novel.",
        "saturation": 0.35, "lightness": 0.08, "contrast": 1.45, "outline": "#0a0a0c", "ramp": None,
    },
}

ORDER = ["classic", "flat", "neon", "noir", "pastel", "ink", "sepia", "gameboy"]


def get(style) -> dict:
    """Accepts a style id, a dict (inline overrides on top of its base), or None."""
    if isinstance(style, dict):
        base = dict(STYLES.get(str(style.get("id") or DEFAULT), STYLES[DEFAULT]))
        base.update({k: v for k, v in style.items() if k != "id"})
        return base
    return STYLES.get(str(style or DEFAULT), STYLES[DEFAULT])


def listing() -> list:
    return [{"id": s, "name": STYLES[s]["name"], "blurb": STYLES[s]["blurb"]} for s in ORDER if s in STYLES]


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in rgb)


def _lum(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def shade_amounts(st) -> tuple[float, float]:
    """The :d / :l shading depths for this style."""
    c = float(st.get("contrast", 1.0))
    return -0.32 * c, 0.30 * c


def outline_color(st, authored: str):
    """The colour an outline pixel should take, or None to leave it transparent."""
    mode = st.get("outline", "dark")
    if mode == "none":
        return None
    if mode == "light":
        return "#e9e4f2"
    if isinstance(mode, str) and mode.startswith("#"):
        return mode
    ramp = st.get("ramp")
    return ramp[0] if ramp else authored


def transform(hexcol: str, st) -> str:
    """Apply a style to one final colour."""
    if not hexcol:
        return hexcol
    ramp = st.get("ramp")
    r, g, b = _hex_to_rgb(hexcol)
    if ramp:
        i = min(len(ramp) - 1, max(0, round(_lum((r, g, b)) * (len(ramp) - 1))))
        return ramp[i]
    sat, lit = float(st.get("saturation", 1.0)), float(st.get("lightness", 0.0))
    if sat == 1.0 and lit == 0.0:
        return hexcol
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    s = max(0.0, min(1.0, s * sat))
    l = max(0.0, min(1.0, l + lit * (1 - l) if lit > 0 else l * (1 + lit)))
    return _rgb_to_hex(colorsys.hls_to_rgb(h, l, s))
