"""Render a theme's admitted parts into themes/<slug>/catalog.html (visual browser)
and themes/<slug>/TEMPLATES.md (reference for the DM).

Only the parts the theme admits are drawn, and they are drawn in the theme's own
palette, so the page looks like the game it belongs to. An "open" theme gets the
whole 211-part library - which is also how you eyeball new templates while working
on engine/core/templates.py.

    python engine/tools/build_catalog.py              # every theme
    python engine/tools/build_catalog.py vantablack-city
"""
import os, sys, json, html
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core import store, assets, library
from core import style as _style

ORDER = ["character", "portrait", "creature", "tile", "object", "item", "icon", "backdrop"]

CSS = ("body{background:%(bg)s;color:%(text)s;font-family:monospace;padding:20px}"
       "h1{color:%(accent)s}h2{color:%(accent)s;border-bottom:2px solid %(panel)s}"
       ".g{display:flex;flex-wrap:wrap;gap:10px}"
       ".c{background:%(panel)s;border:2px solid %(accent)s33;padding:8px;text-align:center;width:150px}"
       ".c svg{max-width:130px;max-height:150px;height:auto}.c.bd{width:310px}.c.bd svg{max-width:290px}"
       ".n{font-size:12px;color:%(accent)s}.d{font-size:11px;color:%(text)s99}"
       ".tag{font-size:10px;color:%(text)s66}.note{color:%(text)s99;font-size:13px}")


def _card(svg, name, desc, wide=False):
    return (f"<div class='c{' bd' if wide else ''}'>{svg}<div class=n>{html.escape(name)}</div>"
            f"<div class=d>{html.escape(desc)}</div></div>")


def build(slug):
    """Build one theme's catalog. Returns the number of parts drawn."""
    theme = assets.load_theme(slug)
    if not theme:
        raise store.DMError(f"no such theme: {slug}")
    pal = theme.get("palette") or {}
    ui = theme.get("ui") or {}
    style = CSS % {"bg": ui.get("bg", "#15121c"), "text": ui.get("text", "#ece6d8"),
                   "panel": ui.get("panel", "#221d2c"), "accent": ui.get("accent", "#c9a24a")}
    tpls = library.templates_for(slug)
    lock = library.summary(slug)
    sty = (theme.get("style") or _style.DEFAULT)
    d = assets.theme_dir(slug)

    h = ["<!doctype html><meta charset=utf-8>",
         f"<title>{html.escape(theme.get('name', slug))} - part catalog</title>",
         f"<style>{style}</style>",
         f"<h1>{html.escape(theme.get('name', slug))}</h1>",
         f"<p class=note>{html.escape(theme.get('description', ''))}</p>",
         f"<p class=note>Vocabulary: <b>{lock['mode']}</b> &middot; {lock['templates']} shared parts admitted"
         f" &middot; art style <b>{html.escape(_style.get(sty)['name'])}</b>"
         f" &middot; drawn in this theme's palette. Recipes reference them as <code>tpl:&lt;name&gt;</code>.</p>"]
    md = [f"# {theme.get('name', slug)} - part catalog", "",
          f"Vocabulary: **{lock['mode']}**, {lock['templates']} shared parts admitted. Art style: **{sty}**.",
          "Reference with `tpl:<name>` in recipes. Colour slots: skin hair top accent legs boots metal wood glow "
          "eyes white mouth primary secondary detail outline.", ""]

    # the theme's own archetypes are the sample mixes - no generic knight/mage
    looks = [(a.get("name", a.get("id", "?")), a.get("look")) for a in theme.get("archetypes", []) if a.get("look")]
    if looks:
        h.append("<h2>Archetypes</h2><div class=g>")
        for name, rec in looks:
            try:
                h.append(_card(assets.render_recipe(slug, rec, pal, scale=6), name, ""))
            except Exception as ex:
                h.append(_card("", name, f"[{type(ex).__name__}]"))
        h.append("</div>")

    # assets this theme created for itself
    own = assets.manifest(slug)["assets"]
    if own:
        h.append(f"<h2>Theme assets ({len(own)})</h2><div class=g>")
        md.append(f"## theme assets ({len(own)})")
        for aid, meta in sorted(own.items()):
            try:
                svg = assets.render_recipe(slug, {"layers": [aid]}, pal,
                                           scale=3 if meta.get("category") == "backdrop" else 6)
            except Exception:
                svg = ""
            h.append(_card(svg, aid, meta.get("desc", ""), meta.get("category") == "backdrop"))
            md.append(f"- `{aid}` ({meta.get('category')}) - {meta.get('desc', '')}")
        h.append("</div>"); md.append("")

    # the admitted shared templates
    by = {}
    for name, t in tpls.items():
        by.setdefault(t["category"], []).append(name)
    n = 0
    for cat in ORDER:
        names = sorted(by.get(cat, []))
        if not names:
            continue
        h.append(f"<h2>{cat} ({len(names)})</h2><div class=g>")
        md.append(f"## {cat}")
        for name in names:
            t = tpls[name]
            try:
                svg = assets.render_recipe(slug, {"layers": ["tpl:" + name]}, pal,
                                           scale=3 if cat == "backdrop" else 6)
            except Exception:
                svg = ""
            h.append(_card(svg, name, t["desc"], cat == "backdrop"))
            p = f" params={json.dumps(t['params'])}" if t["params"] else ""
            md.append(f"- `tpl:{name}` - {t['desc']}{p}")
            n += 1
        h.append("</div>"); md.append("")

    split = library.split_pairs(slug)
    if split:
        warn = ", ".join(f"{a}/{b}" for a, b in split)
        h.append(f"<p class=note>&#9888; sprite/portrait pairs only half-admitted: <b>{html.escape(warn)}</b> "
                 f"&mdash; a character will lose the feature on one of the two.</p>")
        print(f"  ! {slug}: split sprite/portrait pairs: {warn}")
    store.write_text(d / "catalog.html", "\n".join(h))
    store.write_text(d / "TEMPLATES.md", "\n".join(md))
    return n


def build_all():
    out = {}
    for d in (sorted(store.THEMES.iterdir()) if store.THEMES.exists() else []):
        if (d / "theme.json").exists():
            out[d.name] = build(d.name)
    return out


def catalog_path(slug):
    return assets.theme_dir(slug) / "catalog.html"


def is_stale(slug):
    """True when the catalog is missing or older than the theme's definition/assets."""
    c = catalog_path(slug)
    if not c.exists():
        return True
    d = assets.theme_dir(slug)
    newest = max((p.stat().st_mtime for p in (d / "theme.json", d / "manifest.json") if p.exists()), default=0)
    return c.stat().st_mtime < newest


def ensure(slug):
    if is_stale(slug):
        build(slug)
    return catalog_path(slug)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    try:
        if args:
            for s in args:
                print(s, build(s))
        else:
            for s, n in build_all().items():
                print(s, n)
    except store.DMError as e:
        raise SystemExit(str(e))
