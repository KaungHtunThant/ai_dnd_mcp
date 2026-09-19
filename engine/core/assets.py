"""Asset library: theme manifests, part resolution and recipe rendering."""
from __future__ import annotations
import json, functools
from pathlib import Path
from . import store, library
from . import style as _style
from .pixel import Canvas, grid_rects, resolve_colors, svg_doc, render_grid
from .templates import TEMPLATES, build_template

CATEGORIES = ["character", "portrait", "creature", "tile", "object", "item", "icon", "backdrop"]


# ---------------- theme library ----------------
def theme_dir(slug) -> Path:
    return store.THEMES / slug


def load_theme(slug) -> dict:
    return store.read_json(theme_dir(slug) / "theme.json", None)


@functools.lru_cache(maxsize=32)
def _style_for(slug, _theme_stamp, _camp_stamp):
    cid = store.runtime().get("active")
    if cid:
        c = store.read_json(store.CAMPAIGNS / f"{cid}.json", None) or {}
        if c.get("theme") == slug and c.get("style"):
            return c["style"]                      # per-campaign override
    return (load_theme(slug) or {}).get("style") or _style.DEFAULT


def theme_style(slug):
    """The art style for a slug: the active campaign's override if it has one, else the
    theme's own, else 'classic'. Cached on file mtimes so a render is not a file read."""
    if not slug:
        return _style.DEFAULT
    cid = store.runtime().get("active")
    camp = store.CAMPAIGNS / f"{cid}.json" if cid else None
    def m(p):
        try:
            return p.stat().st_mtime if p else 0.0
        except OSError:
            return 0.0
    return _style_for(slug, m(theme_dir(slug) / "theme.json"), m(camp))


def manifest(slug) -> dict:
    m = store.read_json(theme_dir(slug) / "manifest.json", None) or {"assets": {}}
    m.setdefault("assets", {})
    return m


def save_manifest(slug, m):
    store.write_json(theme_dir(slug) / "manifest.json", m)


def asset_path(slug, category, aid) -> Path:
    return theme_dir(slug) / "assets" / category / f"{aid}.json"


def load_asset(slug, aid):
    m = manifest(slug)
    meta = m["assets"].get(aid)
    if not meta:
        return None
    return store.read_json(theme_dir(slug) / meta["file"], None)


# ---------------- part resolution ----------------
@functools.lru_cache(maxsize=2048)
def _tpl_rows(name, params_json):
    return tuple(build_template(name, json.loads(params_json)).rows())


def resolve_part(slug, ref, params=None):
    """Return dict(rows, legend, colors, layer, w, h) or None.
    ref: 'tpl:<template>' | '<theme asset id>'."""
    params = params or {}
    if ref.startswith("tpl:"):
        name = ref[4:]
        t = TEMPLATES.get(name)
        if not t:
            return None
        library.check(slug, name)
        rows = list(_tpl_rows(name, json.dumps(params, sort_keys=True)))
        return {"rows": rows, "legend": {}, "colors": t["colors"], "layer": t["layer"],
                "w": max(len(r) for r in rows), "h": len(rows), "kind": t["kind"]}
    a = load_asset(slug, ref) if slug else None
    if not a:
        # allow bare template names as a convenience
        if ref in TEMPLATES:
            return resolve_part(slug, "tpl:" + ref, params)
        return None
    if a.get("template") and not a.get("rows"):
        base = resolve_part(slug, "tpl:" + a["template"], {**a.get("params", {}), **params})
        if base:
            base["colors"] = {**base["colors"], **a.get("colors", {})}
            base["layer"] = a.get("layer", base["layer"])
        return base
    rows = a["rows"]
    return {"rows": rows, "legend": a.get("legend", {}), "colors": a.get("colors", {}),
            "layer": a.get("layer", 50), "w": max(len(r) for r in rows), "h": len(rows), "kind": a.get("kind", "sprite")}


def _norm_layer(l):
    if isinstance(l, str):
        return {"part": l}
    return dict(l)


def render_recipe(slug, recipe, palette=None, expression=None, scale=1, st=None):
    """Composite a recipe to SVG.
    recipe = {"layers":[ "tpl:body" | {"part":..,"colors":{},"params":{},"dx":0,"dy":0} ],
              "colors":{slot:hex}, "params":{..shared template params..},
              "expression":"neutral", "flip":false, "sort":true}
    A part name may contain '{expr}' which is replaced by the expression."""
    if isinstance(recipe, list):
        recipe = {"layers": recipe}
    if isinstance(recipe, str):
        recipe = {"layers": [recipe]}
    expr = expression or recipe.get("expression") or "neutral"
    st = _style.get(st or recipe.get("style") or theme_style(slug))
    gparams = recipe.get("params", {})
    parts = []
    for i, l in enumerate(recipe.get("layers", [])):
        l = _norm_layer(l)
        if l.get("hidden"):
            continue
        ref = l.get("part", "").replace("{expr}", expr)
        p = resolve_part(slug, ref, {**gparams, **l.get("params", {})})
        if p is None and "{expr}" in l.get("part", ""):
            p = resolve_part(slug, l["part"].replace("{expr}", "neutral"), {})
        if p is None:
            continue
        parts.append((p["layer"] if recipe.get("sort", True) and "z" not in l else l.get("z", 0), i, p, l))
    parts.sort(key=lambda t: (t[0], t[1]))
    if not parts:
        return svg_doc(16, 16, [], scale)
    W = max(p["w"] for _, _, p, _ in parts); H = max(p["h"] for _, _, p, _ in parts)
    body = []
    for _, _, p, l in parts:
        cols = resolve_colors(palette or {}, p["colors"], recipe.get("colors", {}), l.get("colors", {}))
        ox = (W - p["w"]) // 2 + l.get("dx", 0); oy = (H - p["h"]) + l.get("dy", 0)
        body += grid_rects(p["rows"], p["legend"], cols, ox, oy, st=st)
    inner = "".join(body)
    if recipe.get("flip"):
        inner = f'<g transform="translate({W},0) scale(-1,1)">{inner}</g>'
    return svg_doc(W, H, [inner], scale)


# ---------------- search ----------------
def _score(query_terms, text):
    text = text.lower()
    return sum(1 for q in query_terms if q in text)


def find(slug, query="", category=None, tags=None, include_templates=True, limit=30):
    q = [t for t in (query or "").lower().replace(",", " ").split() if t]
    tags = [t.lower() for t in (tags or [])]
    results = []
    if slug:
        for aid, meta in manifest(slug)["assets"].items():
            if category and meta.get("category") != category:
                continue
            hay = " ".join([aid, meta.get("desc", ""), " ".join(meta.get("tags", [])), meta.get("category", "")])
            if tags and not all(t in [x.lower() for x in meta.get("tags", [])] for t in tags):
                continue
            s = _score(q, hay) if q else 1
            if s or not q:
                results.append({"ref": aid, "source": "theme", "category": meta.get("category"),
                                "desc": meta.get("desc", ""), "tags": meta.get("tags", []), "score": s + 0.5})
    if include_templates:
        for name, t in library.templates_for(slug).items():
            if category and t["category"] != category:
                continue
            hay = " ".join([name, t["desc"], " ".join(t["tags"]), t["category"]])
            if tags and not all(x in t["tags"] for x in tags):
                continue
            s = _score(q, hay) if q else 1
            if s or not q:
                results.append({"ref": "tpl:" + name, "source": "template", "category": t["category"],
                                "desc": t["desc"], "tags": t["tags"],
                                "params": t["params"] or None, "score": s})
    results.sort(key=lambda r: -r["score"])
    for r in results:
        r.pop("score", None)
        if r.get("params") is None:
            r.pop("params", None)
    return results[:limit]


def register_asset(slug, aid, category, *, rows=None, legend=None, template=None, params=None,
                   colors=None, tags=None, desc="", layer=None, kind=None):
    """Create/overwrite a theme asset and render a preview SVG next to it."""
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")
    aid = store.slugify(aid).replace("-", "_")
    if template:
        tname = template[4:] if template.startswith("tpl:") else template
        if tname not in TEMPLATES:
            raise ValueError(f"unknown template {template}")
        library.check(slug, tname)
        t = TEMPLATES[tname]
        layer = t["layer"] if layer is None else layer
        kind = kind or t["kind"]
        data = {"id": aid, "category": category, "template": tname, "params": params or {},
                "colors": colors or {}, "layer": layer, "kind": kind}
    else:
        if not rows:
            raise ValueError("either template or rows (pixel grid) is required")
        w = max(len(r) for r in rows)
        rows = [r.ljust(w, ".") for r in rows]
        from .templates import LAYER
        data = {"id": aid, "category": category, "rows": rows, "legend": legend or {},
                "colors": colors or {}, "layer": layer if layer is not None else LAYER.get(category, 50),
                "kind": kind or ("tile" if category == "tile" else "sprite")}
        if params and params.get("outline"):
            data["rows"] = Canvas.from_rows(rows).outline().rows()
    data.update({"tags": tags or [], "desc": desc, "created": store.now_iso()})
    path = asset_path(slug, category, aid)
    store.write_json(path, data)
    m = manifest(slug)
    m["assets"][aid] = {"category": category, "tags": tags or [], "desc": desc,
                        "file": str(path.relative_to(theme_dir(slug))).replace("\\", "/"),
                        "template": data.get("template")}
    save_manifest(slug, m)
    theme = load_theme(slug) or {}
    svg = render_recipe(slug, {"layers": [aid]}, theme.get("palette"), scale=4)
    store.write_text(path.with_suffix(".svg"), svg)
    return aid


# ---------------- maps ----------------
def map_path(slug, mid):
    return theme_dir(slug) / "maps" / f"{mid}.json"


def load_map(slug, mid):
    return store.read_json(map_path(slug, mid), None)


def render_map(slug, m, palette=None, st=None):
    """Whole map as one SVG using <symbol>/<use> per legend char. 16px per tile."""
    st = _style.get(st or theme_style(slug))
    T = 16
    W, H = m["w"], m["h"]
    defs, uses = [], []
    for ch, ent in m.get("legend", {}).items():
        ent = ent if isinstance(ent, dict) else {"tile": ent}
        p = resolve_part(slug, ent.get("tile", "tpl:tile_void"), ent.get("params"))
        if not p:
            continue
        cols = resolve_colors(palette or {}, p["colors"], ent.get("colors", {}))
        sid = "t%d" % ord(ch)
        defs.append(f'<symbol id="{sid}" viewBox="0 0 16 16" width="16" height="16">' +
                    "".join(grid_rects(p["rows"], p["legend"], cols, st=st)) + "</symbol>")
        if ent.get("under"):
            pass
    for y, row in enumerate(m["rows"]):
        for x, ch in enumerate(row):
            ent = m.get("legend", {}).get(ch)
            if ent is None:
                continue
            ent = ent if isinstance(ent, dict) else {"tile": ent}
            if ent.get("under"):
                uses.append(f'<use href="#t{ord(ent["under"])}" x="{x * T}" y="{y * T}"/>')
            uses.append(f'<use href="#t{ord(ch)}" x="{x * T}" y="{y * T}"/>')
    # static decorations
    for o in m.get("objects", []):
        rec = o.get("sprite") or {"layers": [o.get("part")]}
        svg = render_recipe(slug, rec, palette, st=st)
        inner = svg[svg.index(">") + 1:-6]
        vb = svg.split('viewBox="0 0 ')[1].split('"')[0].split()
        w, h = int(vb[0]), int(vb[1])
        uses.append(f'<svg x="{o["x"] * T + (T - w) // 2}" y="{o["y"] * T + T - h}" width="{w}" height="{h}" '
                    f'viewBox="0 0 {w} {h}" overflow="visible">{inner}</svg>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W * T} {H * T}" width="{W * T}" '
            f'height="{H * T}" shape-rendering="crispEdges"><defs>{"".join(defs)}</defs>{"".join(uses)}</svg>')
