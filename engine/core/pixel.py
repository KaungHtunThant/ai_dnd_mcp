"""Pixel canvas + SVG rendering.

A part is a grid of characters. Each character maps (via a legend) to a colour
slot name ("skin", "hair:d") or a literal hex colour. '.' or ' ' is transparent.
Slots ending in ':d' / ':l' are auto-shaded (darker / lighter) from the base slot,
so recolouring one slot recolours its shading too.
"""
from __future__ import annotations
import colorsys, math, random
from . import style as _style

# ---- standard legend used by every template -------------------------------
STD_LEGEND = {
    "o": "outline",
    "s": "skin", "S": "skin:d", "c": "skin:l",
    "h": "hair", "H": "hair:d", "j": "hair:l",
    "t": "top", "T": "top:d", "u": "top:l",
    "a": "accent", "A": "accent:d", "v": "accent:l",
    "l": "legs", "L": "legs:d",
    "b": "boots", "B": "boots:d",
    "m": "metal", "M": "metal:d", "n": "metal:l",
    "w": "wood", "W": "wood:d", "i": "wood:l",
    "g": "glow", "G": "glow:d", "f": "glow:l",
    "e": "eyes", "y": "white", "r": "mouth", "x": "shadow",
    "p": "primary", "P": "primary:d", "q": "primary:l",
    "k": "secondary", "K": "secondary:d", "z": "secondary:l",
    "d": "detail", "D": "detail:d",
}

DEFAULT_COLORS = {
    "outline": "#1a1523", "skin": "#e0a878", "hair": "#5a3a22", "top": "#3d6fa8",
    "accent": "#c9a24a", "legs": "#4a4358", "boots": "#5b3a26", "metal": "#9aa4b1",
    "wood": "#8a5a34", "glow": "#7fe3ff", "eyes": "#2a2233", "white": "#f4f1ea",
    "mouth": "#8c3040", "shadow": "#000000", "primary": "#6b6f7e", "secondary": "#4f8a4b",
    "detail": "#d8c9a8",
}


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in rgb)


def shade(hexcol: str, amount: float) -> str:
    """amount <0 darker, >0 lighter. Hue-shifts slightly like pixel artists do."""
    r, g, b = _hex_to_rgb(hexcol)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if amount < 0:
        l = max(0.0, l * (1 + amount))
        h = (h + 0.02 * amount) % 1.0  # toward blue/purple in shadow
        s = min(1.0, s * 1.05)
    else:
        l = min(1.0, l + (1 - l) * amount)
        h = (h - 0.015 * amount) % 1.0  # toward yellow in light
    return _rgb_to_hex(colorsys.hls_to_rgb(h, l, s))


def norm_hex(v: str) -> str:
    v = v.strip()
    if not v.startswith("#"):
        v = "#" + v
    if len(v) == 4:
        v = "#" + "".join(c * 2 for c in v[1:])
    return v.lower()[:7]


def resolve_colors(*layers: dict) -> dict:
    out = dict(DEFAULT_COLORS)
    for layer in layers:
        if layer:
            out.update({k: norm_hex(v) for k, v in layer.items() if isinstance(v, str) and v})
    return out


def color_of(token: str, colors: dict, st=None) -> str | None:
    """Final colour for one legend token. `st` is an art style (see core/style.py):
    it sets how deep the automatic :d / :l shading goes, what an outline pixel does,
    and a transform applied to every resulting colour."""
    st = _style.get(st) if not isinstance(st, dict) or "saturation" not in (st or {}) else st
    if token.startswith("#"):
        return _style.transform(norm_hex(token), st)
    base, _, mod = token.partition(":")
    col = colors.get(token) or colors.get(base) or DEFAULT_COLORS.get(base)
    if col is None:
        return None
    if base == "outline":
        return _style.outline_color(st, col)
    if token in colors:  # explicit shade given
        return _style.transform(col, st)
    if mod in ("d", "l"):
        dark, light = _style.shade_amounts(st)
        col = shade(col, dark if mod == "d" else light)
    return _style.transform(col, st)


# ---- canvas ---------------------------------------------------------------
class Canvas:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.g = [["."] * w for _ in range(h)]

    # basic ops
    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = c
        return self

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y][x]
        return "."

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.px(xx, yy, c)
        return self

    def hline(self, x0, x1, y, c):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.px(x, y, c)
        return self

    def vline(self, x, y0, y1, c):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.px(x, y, c)
        return self

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy; x0 += sx
            if e2 <= dx:
                err += dx; y0 += sy
        return self

    def ellipse(self, cx, cy, rx, ry, c, fill=True):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                d = ((x - cx) / max(rx, 0.01)) ** 2 + ((y - cy) / max(ry, 0.01)) ** 2
                if fill and d <= 1.0:
                    self.px(x, y, c)
                elif not fill and 0.7 <= d <= 1.15:
                    self.px(x, y, c)
        return self

    def poly(self, pts, c):
        """Filled polygon (scanline, pixel centres)."""
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            yc = y + 0.5
            xs = []
            n = len(pts)
            for i in range(n):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[i] - 0.5)), int(math.floor(xs[i + 1] - 0.5)) + 1):
                    self.px(x, y, c)
        return self

    def replace(self, old, new, mask=None):
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] == old and (mask is None or mask(x, y)):
                    self.g[y][x] = new
        return self

    def noise(self, targets: str, new: str, density=0.15, seed=0, mask=None):
        rnd = random.Random(seed)
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] in targets and rnd.random() < density and (mask is None or mask(x, y)):
                    self.g[y][x] = new
        return self

    def mirror(self):
        """Copy left half onto right half (symmetry)."""
        for y in range(self.h):
            for x in range(self.w // 2):
                self.g[y][self.w - 1 - x] = self.g[y][x]
        return self

    def outline(self, c="o", diagonal=False, skip=""):
        filled = {(x, y) for y in range(self.h) for x in range(self.w)
                  if self.g[y][x] not in ". " and self.g[y][x] != c and self.g[y][x] not in skip}
        nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if diagonal:
            nb += [(1, 1), (-1, -1), (1, -1), (-1, 1)]
        for (x, y) in list(filled):
            for dx, dy in nb:
                xx, yy = x + dx, y + dy
                if 0 <= xx < self.w and 0 <= yy < self.h and self.g[yy][xx] == ".":
                    self.g[yy][xx] = c
        return self

    def shade_bottom_right(self, base, dark, rows_from=None):
        """Put dark variant on right/bottom edges of regions of `base`."""
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] == base:
                    r = self.get(x + 1, y)
                    b = self.get(x, y + 1)
                    if r not in (base, dark) or b not in (base, dark):
                        self.g[y][x] = dark
        return self

    def paste(self, other: "Canvas", ox=0, oy=0):
        for y in range(other.h):
            for x in range(other.w):
                c = other.g[y][x]
                if c not in ". ":
                    self.px(x + ox, y + oy, c)
        return self

    def flip(self):
        for row in self.g:
            row.reverse()
        return self

    def rows(self):
        return ["".join(r) for r in self.g]

    @staticmethod
    def from_rows(rows):
        h = len(rows); w = max(len(r) for r in rows) if rows else 0
        cv = Canvas(w, h)
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                cv.g[y][x] = "." if ch == " " else ch
        return cv


# ---- SVG ------------------------------------------------------------------
def grid_rects(rows, legend, colors, ox=0, oy=0, flip=False, w=None, st=None):
    """Return list of svg <rect> strings, merging horizontal runs."""
    legend = {**STD_LEGEND, **(legend or {})}
    out = []
    width = w or (max(len(r) for r in rows) if rows else 0)
    for y, row in enumerate(rows):
        if flip:
            row = row.ljust(width, ".")[::-1]
        x = 0
        n = len(row)
        while x < n:
            ch = row[x]
            if ch in ". ":
                x += 1
                continue
            tok = legend.get(ch)
            if tok is None:
                x += 1
                continue
            col = color_of(tok, colors, st)
            if col is None:
                x += 1
                continue
            x2 = x + 1
            while x2 < n and row[x2] == ch:
                x2 += 1
            op = ""
            if tok.startswith("shadow"):
                op = ' fill-opacity="0.35"'
            out.append(f'<rect x="{x + ox}" y="{y + oy}" width="{x2 - x}" height="1" fill="{col}"{op}/>')
            x = x2
    return out


def svg_doc(w, h, body, scale=1):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w * scale}" height="{h * scale}" shape-rendering="crispEdges">'
            + "".join(body) + "</svg>")


def render_grid(rows, legend=None, colors=None, scale=1, st=None):
    w = max(len(r) for r in rows) if rows else 1
    h = len(rows)
    return svg_doc(w, h, grid_rects(rows, legend, resolve_colors(colors), st=st), scale)
