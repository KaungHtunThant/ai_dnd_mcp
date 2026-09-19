"""Theme-locked part vocabulary.

Every theme declares which shared templates it is allowed to use, in
theme.json["library"]:

    "library": {
      "mode": "locked",                      # "locked" | "open"  (default: open)
      "core": true,                          # admit the structural universals
      "include_tags": ["scifi", "cyber"],    # any template carrying one of these tags
      "include": ["tpl:obj_*", "cr_drone"],  # explicit names or globs
      "exclude": ["hair_bun"]                # applied last, beats everything
    }

Resolved set = (core if core else {}) | tag matches | include  -  exclude.

A theme with no library block, or mode != "locked", admits every template -
the behaviour from before the lock existed - so old themes keep working.
"""
from __future__ import annotations
import fnmatch, functools
from . import store
from .templates import TEMPLATES


class NotInTheme(store.DMError):
    """A recipe referenced a real template that the active theme does not admit."""


# ---- the structural universals ------------------------------------------
# Scaffolding that is genre-neutral and that the engine's own defaults rely on
# (stat/resource/condition icons, the face set, a body to hang clothes on, and
# tile_void, which render_map falls back to). `exclude` can still strip any of it.
CORE_CATEGORIES = {"icon"}
CORE_PREFIXES = ("p_face_",)
CORE_NAMES = {
    "body", "legs_pants", "legs_skirt", "boots", "top_shirt", "beard",
    "hair_bun", "hair_curly", "hair_long", "hair_mohawk", "hair_ponytail", "hair_short", "hair_spiky",
    "p_base", "p_hair_back", "p_beard", "p_mustache", "p_outfit_shirt", "p_scar",
    "p_hair_bob", "p_hair_bun", "p_hair_curly", "p_hair_long", "p_hair_mohawk",
    "p_hair_short", "p_hair_slick", "p_hair_spiky",
    "tile_void",
}


def core_names() -> set[str]:
    return {n for n, t in TEMPLATES.items()
            if t["category"] in CORE_CATEGORIES or n.startswith(CORE_PREFIXES) or n in CORE_NAMES}


# ---- resolution ----------------------------------------------------------
def bare(ref: str) -> str:
    """'tpl:body' -> 'body'."""
    return ref[4:] if ref.startswith("tpl:") else ref


def _match(patterns, name) -> bool:
    return any(fnmatch.fnmatchcase(name, bare(str(p))) for p in patterns)


def _stamp(slug) -> float:
    try:
        return (store.THEMES / slug / "theme.json").stat().st_mtime
    except OSError:
        return 0.0


@functools.lru_cache(maxsize=64)
def _resolve(slug, stamp):
    """None = open (everything admitted); otherwise the admitted template names."""
    t = store.read_json(store.THEMES / slug / "theme.json", None) or {}
    cfg = t.get("library") or {}
    if str(cfg.get("mode", "open")).lower() != "locked":
        return None
    names = core_names() if cfg.get("core", True) else set()
    tags = {str(x).lower() for x in (cfg.get("include_tags") or [])}
    if tags:
        names |= {n for n, tpl in TEMPLATES.items() if tags & {x.lower() for x in tpl["tags"]}}
    inc = cfg.get("include") or []
    if inc:
        names |= {n for n in TEMPLATES if _match(inc, n)}
    exc = cfg.get("exclude") or []
    if exc:
        names -= {n for n in names if _match(exc, n)}
    return frozenset(names)


def allowed(slug):
    """Admitted template names for a theme, or None when the theme is open.
    Cached on theme.json's mtime, so update_theme invalidates it for free."""
    return _resolve(slug, _stamp(slug)) if slug else None


def admits(slug, ref) -> bool:
    a = allowed(slug)
    return True if a is None else bare(ref) in a


def check(slug, ref):
    """Raise NotInTheme if a known template is outside the theme's vocabulary."""
    if not admits(slug, ref):
        raise NotInTheme(
            f"'{ref}' is not in theme '{slug}'. Use find_assets to see what this theme admits, "
            f"or add it to theme.json library.include / library.include_tags via update_theme.")


def templates_for(slug) -> dict:
    a = allowed(slug)
    return dict(TEMPLATES) if a is None else {n: t for n, t in TEMPLATES.items() if n in a}


# expressions a recipe's "{expr}" may expand to, so a recipe is checked for all of them
EXPRESSIONS = ("neutral", "happy", "laugh", "angry", "sad", "surprised",
               "smirk", "hurt", "calm", "determined", "scared")


def check_recipe(slug, recipe, where=""):
    """Validate every part a recipe references, so a locked theme refuses at the tool
    boundary instead of storing something that will not draw. Unknown parts are left
    alone - only real templates outside the vocabulary raise."""
    if not slug or allowed(slug) is None or not recipe:
        return
    if isinstance(recipe, str):
        recipe = {"layers": [recipe]}
    if isinstance(recipe, list):
        recipe = {"layers": recipe}
    if not isinstance(recipe, dict):
        return
    for layer in recipe.get("layers") or []:
        ref = layer if isinstance(layer, str) else (layer or {}).get("part", "")
        if not isinstance(ref, str) or not ref:
            continue
        refs = [ref.replace("{expr}", e) for e in EXPRESSIONS] if "{expr}" in ref else [ref]
        for r in refs:
            if bare(r) in TEMPLATES and not admits(slug, r):
                raise NotInTheme(
                    f"{where or 'recipe'}: '{r}' is not in theme '{slug}'. Use find_assets to see what this theme "
                    f"admits, or add it via update_theme({{'library': {{'include': ['{bare(r)}']}}}}).")


def split_pairs(slug) -> list[tuple[str, str]]:
    """Sprite/portrait counterparts where only one half is admitted (e.g. 'eyepatch' without
    'p_eyepatch'), which shows up as a character whose portrait quietly loses a feature."""
    a = allowed(slug)
    if a is None:
        return []
    out = []
    for n in TEMPLATES:
        if not n.startswith("p_"):
            continue
        stem = n[2:]
        if stem in TEMPLATES and (n in a) != (stem in a):
            out.append((stem, n))
    return sorted(out)


def summary(slug) -> dict:
    a = allowed(slug)
    if a is None:
        return {"mode": "open", "templates": len(TEMPLATES)}
    by = {}
    for n in sorted(a):
        by.setdefault(TEMPLATES[n]["category"], []).append(n)
    return {"mode": "locked", "templates": len(a), "by_category": by}
