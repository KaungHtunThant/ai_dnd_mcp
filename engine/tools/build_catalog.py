"""Render every shared template inline into
shared/catalog.html (visual browser) + engine/TEMPLATES.md (reference for the DM)."""
import os, sys, json, html
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core import store, assets
from core.templates import TEMPLATES

def build():
    out = store.SHARED / "templates"
    cats = {}
    for name, t in TEMPLATES.items():
        cats.setdefault(t["category"], []).append(name)
        scale = 3 if t["category"] == "backdrop" else 6
        t["_svg"] = assets.render_recipe(None, {"layers": ["tpl:" + name]}, None, scale=scale)

    # sample composites so the mix-and-match idea is visible
    samples = {
     "knight": ["tpl:cloak", "tpl:body", "tpl:legs_pants", "tpl:boots", "tpl:top_armor", "tpl:hat_helmet", "tpl:held_sword", "tpl:offhand_shield"],
     "mage": {"layers": ["tpl:body", "tpl:top_robe", "tpl:beard", "tpl:hair_long", "tpl:hat_wizard", "tpl:held_staff"], "colors": {"top": "#4a3a8a", "hair": "#ddd", "accent": "#d4b24a"}},
     "netrunner": {"layers": ["tpl:body", "tpl:legs_pants", "tpl:boots", "tpl:top_jacket", "tpl:hair_spiky", "tpl:goggles", "tpl:held_gun"], "colors": {"hair": "#e04a8a", "top": "#222", "accent": "#39f", "glow": "#3aff9a"}},
     "gunslinger": {"layers": ["tpl:body", "tpl:legs_pants", "tpl:boots", "tpl:top_coat", "tpl:hair_long", "tpl:hat_wide", "tpl:held_rifle"], "colors": {"top": "#6b4a2e", "accent": "#3a2d25", "skin": "#8d5a3b"}},
     "portrait_knight": {"layers": ["tpl:p_base", "tpl:p_face_determined", "tpl:p_outfit_armor", "tpl:p_hat_helmet"]},
     "portrait_mage": {"layers": ["tpl:p_hair_back", "tpl:p_base", "tpl:p_face_smirk", "tpl:p_outfit_robe", "tpl:p_hair_long", "tpl:p_hat_wizard"], "colors": {"hair": "#ddd", "top": "#4a3a8a"}},
     "portrait_runner": {"layers": ["tpl:p_base", "tpl:p_face_happy", "tpl:p_outfit_hoodie", "tpl:p_hair_spiky", "tpl:p_visor"], "colors": {"hair": "#e04a8a", "top": "#222", "glow": "#3aff9a"}},
    }
    sample_svg = {k: assets.render_recipe(None, r, None, scale=6) for k, r in samples.items()}

    order = ["character", "portrait", "creature", "tile", "object", "item", "icon", "backdrop"]
    h = ["<!doctype html><meta charset=utf-8><title>Claude DnD - shared template library</title>",
         "<style>body{background:#15121c;color:#ece6d8;font-family:monospace;padding:20px}h2{color:#c9a24a;border-bottom:2px solid #3a3348}"
         ".g{display:flex;flex-wrap:wrap;gap:10px}.c{background:#221d2c;border:2px solid #3a3348;padding:8px;text-align:center;width:150px}"
         ".c svg{max-width:130px;max-height:150px;height:auto}.c.bd{width:310px}.c.bd svg{max-width:290px}.n{font-size:12px;color:#c9a24a}.d{font-size:11px;color:#9a93a8}</style>",
         "<h1>Claude DnD - shared template library</h1><p>Every part is recolourable and mixable. Recipes reference them as <code>tpl:&lt;name&gt;</code>.</p>",
         "<h2>Sample mixes</h2><div class=g>"]
    for k in samples:
        h.append(f"<div class=c>{sample_svg[k]}<div class=n>{k}</div></div>")
    h.append("</div>")
    md = ["# Shared template library", "", "Reference with `tpl:<name>` in recipes. Colour slots: skin hair top accent legs boots metal wood glow eyes white mouth primary secondary detail outline.", ""]
    for cat in order:
        names = cats.get(cat, [])
        h.append(f"<h2>{cat} ({len(names)})</h2><div class=g>")
        md.append(f"## {cat}")
        for n in names:
            t = TEMPLATES[n]
            h.append(f"<div class='c {'bd' if cat == 'backdrop' else ''}'>{t['_svg']}<div class=n>{n}</div><div class=d>{html.escape(t['desc'])}</div></div>")
            p = f" params={json.dumps(t['params'])}" if t["params"] else ""
            md.append(f"- `tpl:{n}` - {t['desc']}{p}")
        h.append("</div>"); md.append("")
    store.write_text(store.SHARED / "catalog.html", "\n".join(h))
    store.write_text(store.ENGINE / "TEMPLATES.md", "\n".join(md))
    print("templates:", len(TEMPLATES))

    return len(TEMPLATES)


if __name__ == "__main__":
    build()
