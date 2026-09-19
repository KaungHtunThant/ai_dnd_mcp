"""All DM tools. Shared by the MCP server (mcp_server.py) and the CLI (dm.py).

Every public function registered with @tool becomes an MCP tool of the same
name. Functions return JSON-serialisable dicts.
"""
from __future__ import annotations
import copy, contextlib, random
from pathlib import Path
from . import store, assets, dice, tts
import time as _time
from .store import slugify, now_iso

TOOLS: dict[str, callable] = {}
UI_HOOK = {"ensure_ui": None}   # set by mcp_server to start the UI server


def tool(fn):
    TOOLS[fn.__name__] = fn
    return fn


class DMError(Exception):
    pass


# =====================================================================
# helpers
# =====================================================================
DEFAULT_STATS = [
    {"key": "str", "name": "Strength", "abbr": "STR", "icon": "tpl:ic_fist"},
    {"key": "dex", "name": "Dexterity", "abbr": "DEX", "icon": "tpl:ic_feather"},
    {"key": "con", "name": "Constitution", "abbr": "CON", "icon": "tpl:ic_heart"},
    {"key": "int", "name": "Intelligence", "abbr": "INT", "icon": "tpl:ic_brain"},
    {"key": "wis", "name": "Wisdom", "abbr": "WIS", "icon": "tpl:ic_eye"},
    {"key": "cha", "name": "Charisma", "abbr": "CHA", "icon": "tpl:ic_mask"},
]
DEFAULT_RESOURCES = [
    {"key": "hp", "name": "HP", "icon": "tpl:ic_heart", "color": "#e0304a"},
]
DEFAULT_CONDITIONS = {
    "poisoned": "tpl:ic_poison", "burning": "tpl:ic_flame", "stunned": "tpl:ic_stun", "blessed": "tpl:ic_halo",
    "cursed": "tpl:ic_skull", "bleeding": "tpl:ic_blood", "frozen": "tpl:ic_snow", "hidden": "tpl:ic_eye_closed",
    "asleep": "tpl:ic_sleep", "frightened": "tpl:ic_fear", "charmed": "tpl:ic_charm", "exhausted": "tpl:ic_sweat",
    "restrained": "tpl:ic_chain", "prone": "tpl:ic_arrow_down", "slowed": "tpl:ic_hourglass",
    "hasted": "tpl:ic_run", "inspired": "tpl:ic_music", "invisible": "tpl:ic_eye_closed",
}


def _deep_merge(dst, src):
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        elif v is None:
            dst.pop(k, None)
        else:
            dst[k] = v
    return dst


def _campaign_path(cid):
    return store.CAMPAIGNS / f"{cid}.json"


def _active_id():
    cid = store.runtime().get("active")
    if not cid:
        raise DMError("No active campaign. Call init, then new_campaign or load_campaign.")
    return cid


def _load(cid=None):
    cid = cid or _active_id()
    c = store.read_json(_campaign_path(cid), None)
    if c is None:
        raise DMError(f"campaign '{cid}' not found")
    return c


def _save(c):
    c["updated"] = now_iso()
    store.write_json(_campaign_path(c["id"]), c)


@contextlib.contextmanager
def _campaign():
    c = _load()
    yield c
    _save(c)


def _theme(c):
    t = assets.load_theme(c["theme"])
    if not t:
        raise DMError(f"theme '{c['theme']}' missing")
    return t


def _log(c, kind, text, **extra):
    c.setdefault("log", []).append({"turn": c.get("turn", 0), "kind": kind, "text": text, "t": now_iso(), **extra})
    c["log"] = c["log"][-400:]


def _find_actor(c, target):
    """player | companion id | scene entity id -> (dict, kind)."""
    if target in (None, "", "player", "me", "pc"):
        return c["character"], "player"
    for comp in c.get("party", []):
        if comp.get("id") == target:
            return comp, "companion"
    for e in c["scene"].get("entities", []):
        if e.get("id") == target:
            return e, "entity"
    raise DMError(f"no actor '{target}' (player, companion ids: {[p.get('id') for p in c.get('party', [])]}, "
                  f"entity ids: {[e.get('id') for e in c['scene'].get('entities', [])]})")


def _new_character():
    return {"name": "", "pronouns": "", "archetype": "", "level": 1, "xp": 0, "stats": {},
            "resources": {}, "conditions": [], "inventory": [], "equipment": {}, "currency": 0,
            "abilities": [], "sprite": {"layers": []}, "portrait": {"layers": []}, "backstory": "", "hooks": []}


def _strip_for_ui(c):
    out = {k: v for k, v in c.items() if k not in ("dm", "snapshots")}
    out["log"] = c.get("log", [])[-120:]
    out["rolls"] = [r for r in c.get("rolls", [])[-40:] if not r.get("hidden")]
    out["ooc"] = c.get("ooc", [])[-80:]
    return out


# =====================================================================
# SETUP
# =====================================================================
INIT_STEPS = [
    {"step": "1_theme", "ask": "Which theme? Offer the existing themes (reused as-is) or let the player describe a "
                             "new one in their own words (any genre: fantasy, cyberpunk, cosmic horror, western, space opera...)."},
    {"step": "2_tone", "ask": "Tone (grim / heroic / pulpy / comedic / horror), content limits (lines & veils), difficulty "
                            "(story / standard / brutal), permadeath strictness, and preferred session length."},
    {"step": "3_character", "ask": "Name, pronouns, archetype (offer 3-5 theme-fitting archetypes from theme.json), "
                                 "stats method (roll 4d6kh3 / point-buy / standard array 15,14,13,12,10,8), look "
                                 "(use showcase() to present sprite/portrait options; update set_character live), "
                                 "and 1-3 backstory hooks."},
    {"step": "4_party", "ask": "Solo, or 1-2 DM-run companions? (add_companion)"},
    {"step": "5_build", "ask": "No question. DM: new theme -> create only the starter kit it truly needs; write the "
                             "secret scenario into dm_notes; finish_setup; then play the opening scene."},
]


@tool
def init() -> dict:
    """Connect the DM at the start of a chat session (player says 'go'/'init'). Ensures the browser UI is running and
    returns the UI url, themes, saves and the flow. Setup now happens in the BROWSER main menu (New Game wizard /
    Continue / Settings): after init, enter the await_action loop and handle menu requests (build_theme, new_game,
    resume) plus in-game Speak/Do/DM actions. INIT_STEPS below are only a fallback for chat-only play."""
    store.ensure_dirs()
    url = None
    if UI_HOOK.get("ensure_ui"):
        url = UI_HOOK["ensure_ui"]()
    cfg = store.config()
    url = url or f"http://{cfg['ui_host']}:{cfg['ui_port']}/"
    return {"ui_url": url, "flow": "browser menu - call await_action(50) in a loop; see CLAUDE.md section 2", "themes": list_themes()["themes"], "campaigns": list_campaigns()["campaigns"],
            "steps": INIT_STEPS,
            "rules": "Ask setup questions in chat one step at a time. Reuse theme assets first (find_assets / "
                     "find_maps / find_npcs / find_lore); create_* only when nothing suitable exists. Keep secrets in "
                     "dm_notes. After each resolved player action call end_turn(summary)."}


@tool
def list_themes() -> dict:
    """List theme libraries (folders under themes/) with a summary of what each already contains."""
    out = []
    if store.THEMES.exists():
        for d in sorted(store.THEMES.iterdir()):
            t = store.read_json(d / "theme.json", None)
            if not t:
                continue
            m = assets.manifest(d.name)
            out.append({"slug": d.name, "name": t.get("name"), "description": t.get("description", ""),
                        "assets": len(m["assets"]), "maps": len(list((d / "maps").glob("*.json"))),
                        "npcs": len(list((d / "npcs").glob("*.json"))), "lore": len(list((d / "lore").glob("*.md")))})
    return {"themes": out}


@tool
def theme_info(theme: str) -> dict:
    """Full theme.json plus an inventory of the theme library (asset ids by category, maps, npcs, lore, tables)."""
    t = assets.load_theme(theme)
    if not t:
        raise DMError(f"theme '{theme}' not found")
    d = assets.theme_dir(theme); m = assets.manifest(theme)
    by = {}
    for aid, meta in m["assets"].items():
        by.setdefault(meta["category"], []).append(aid)
    return {"theme": t, "assets": by,
            "maps": [p.stem for p in (d / "maps").glob("*.json")],
            "npcs": [p.stem for p in (d / "npcs").glob("*.json")],
            "lore": [p.stem for p in (d / "lore").glob("*.md")],
            "tables": [p.stem for p in (d / "tables").glob("*.json")]}


@tool
def create_theme(name: str, description: str, palette: dict | None = None, stats: list | None = None,
                 resources: list | None = None, currency: dict | None = None, archetypes: list | None = None,
                 conditions: dict | None = None, ui: dict | None = None, tone: str = "", terms: dict | None = None) -> dict:
    """Create a NEW theme folder (only if no existing theme fits). Everything is reused by later campaigns.
    palette: default colour slots, e.g. {"outline":"#1a1523","skin":"#e0a878","top":"#3d6fa8","accent":"#c9a24a",
      "metal":"#9aa4b1","glow":"#7fe3ff","primary":"#6b6f7e","secondary":"#4f8a4b"}.
    stats: 6 items [{"key","name","abbr","icon":"tpl:ic_fist"}] (keys are used in character.stats). Default D&D six.
    resources: [{"key":"hp","name":"Health","icon":"tpl:ic_heart","color":"#e0304a"}, {"key":"sanity",...}].
    currency: {"name":"credits","icon":"tpl:item_coins"}. archetypes: [{"id","name","desc","stat_bonus":{},"start_items":[],"look":{sprite recipe hint}}].
    conditions: {name: icon ref} extra/renamed conditions. ui: {"accent":"#hex","bg":"#hex","panel":"#hex","text":"#hex",
      "font":"pixel|serif|mono|sans","title_font":...}. terms: rename UI words, e.g. {"journal":"Case Notes","quests":"Leads"}."""
    slug = slugify(name)
    d = assets.theme_dir(slug)
    if (d / "theme.json").exists():
        raise DMError(f"theme '{slug}' already exists - reuse it (theme_info) or update_theme")
    for sub in ("assets", "maps", "npcs", "lore", "tables"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    t = {"slug": slug, "name": name, "description": description, "tone": tone, "created": now_iso(),
         "palette": palette or {}, "stats": stats or DEFAULT_STATS, "resources": resources or DEFAULT_RESOURCES,
         "currency": currency or {"name": "gold", "icon": "tpl:ic_coin"}, "archetypes": archetypes or [],
         "conditions": {**DEFAULT_CONDITIONS, **(conditions or {})},
         "ui": {"accent": "#c9a24a", "bg": "#15121c", "panel": "#221d2c", "text": "#ece6d8", "font": "pixel", **(ui or {})},
         "terms": terms or {}, "voices": {"narrator": dict(tts.DEFAULT_NARRATOR)}}
    store.write_json(d / "theme.json", t)
    assets.save_manifest(slug, {"assets": {}})
    return {"slug": slug, "path": str(d)}


@tool
def update_theme(theme: str, changes: dict) -> dict:
    """Deep-merge changes into a theme's theme.json (e.g. add an archetype, tweak palette/ui). Lists are replaced."""
    p = assets.theme_dir(theme) / "theme.json"
    t = store.read_json(p, None)
    if not t:
        raise DMError("theme not found")
    _deep_merge(t, changes)
    store.write_json(p, t); store.touch()
    return {"ok": True, "theme": t}


@tool
def list_campaigns() -> dict:
    """List campaign files in campaigns/ with status."""
    out = []
    if store.CAMPAIGNS.exists():
        for p in sorted(store.CAMPAIGNS.glob("*.json")):
            c = store.read_json(p, {})
            out.append({"id": c.get("id"), "name": c.get("name"), "theme": c.get("theme"), "status": c.get("status"),
                        "character": c.get("character", {}).get("name"), "turn": c.get("turn"), "updated": c.get("updated")})
    return {"campaigns": out, "active": store.runtime().get("active")}


@tool
def new_campaign(name: str, theme: str, settings: dict | None = None, player: dict | None = None) -> dict:
    """Create campaigns/<id>.json for a new campaign in an existing theme and make it active (status 'setup').
    settings: {"tone","difficulty","permadeath","content_limits":[...],"session_length"}.
    player: info about the real player (name, preferences)."""
    if not assets.load_theme(theme):
        raise DMError(f"theme '{theme}' not found; create_theme first")
    cid = f"{slugify(name)}-{__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M')}"
    c = {"id": cid, "name": name, "theme": theme, "status": "setup", "created": now_iso(), "updated": now_iso(),
         "settings": settings or {}, "player": player or {}, "turn": 0,
         "character": _new_character(), "party": [], "runs": [], "legacy": [],
         "world": {"map": None, "pos": None, "maps": {}, "flags": {}, "npcs": {}, "time": "", "weather": "",
                   "location": ""},
         "quests": [], "journal": [], "log": [], "rolls": [],
         "scene": {"mode": "setup", "title": "", "backdrop": None, "entities": [], "dialogue": None, "showcase": None},
         "combat": {"active": False, "round": 0, "order": [], "turn_index": 0},
         "dm": {"scenario": {}, "secrets": [], "notes": [], "plans": []}, "snapshots": [],
         "ooc": [], "previously": ""}
    store.write_json(_campaign_path(cid), c)
    store.set_active(cid)
    return {"campaign_id": cid, "file": str(_campaign_path(cid))}


@tool
def load_campaign(campaign_id: str) -> dict:
    """Make an existing campaign active and display it."""
    c = _load(campaign_id)
    store.set_active(campaign_id)
    return {"ok": True, "status": c["status"], "summary": _summary(c)}


def _summary(c):
    ch = c["character"]
    return {"name": c["name"], "theme": c["theme"], "status": c["status"], "turn": c["turn"],
            "character": {k: ch.get(k) for k in ("name", "archetype", "level", "resources", "conditions")},
            "location": c["world"].get("location"), "map": c["world"].get("map"), "pos": c["world"].get("pos"),
            "open_quests": [q["title"] for q in c.get("quests", []) if q.get("status") == "active"],
            "last_log": c.get("log", [])[-6:]}


@tool
def set_character(fields: dict, target: str = "player") -> dict:
    """Deep-merge fields into the player character (or a companion id). Used live during character creation so the
    setup screen previews it. Fields: name, pronouns, archetype, level, xp, stats{key:int}, resources{key:{cur,max}},
    inventory[list], equipment{}, currency, abilities[], backstory, hooks[],
    sprite: recipe {"layers":["tpl:body","tpl:legs_pants","tpl:boots","tpl:top_shirt","tpl:hair_short"],"colors":{"skin":"#c98e62","hair":"#2a1a10","top":"#3d6fa8"},"params":{"build":"normal"}},
    portrait: recipe {"layers":["tpl:p_base","tpl:p_face_{expr}","tpl:p_outfit_shirt","tpl:p_hair_short"],"colors":{...}}.
    Setting a recipe replaces it (lists replace)."""
    with _campaign() as c:
        actor, _ = _find_actor(c, target)
        for k in ("sprite", "portrait"):
            if k in fields and isinstance(fields[k], (list, str)):
                fields[k] = {"layers": fields[k] if isinstance(fields[k], list) else [fields[k]]}
        _deep_merge(actor, fields)
    store.push_event("character", {"target": target})
    return {"ok": True, "character": actor}


@tool
def add_companion(companion: dict) -> dict:
    """Add a DM-run companion to the party. companion: {id,name,archetype,personality,stats,resources,sprite,portrait,attitude(-100..100)}"""
    with _campaign() as c:
        comp = {**_new_character(), "attitude": 0, **companion}
        comp["id"] = slugify(comp.get("id") or comp.get("name"))
        c["party"] = [p for p in c["party"] if p["id"] != comp["id"]] + [comp]
        _log(c, "system", f"{comp.get('name')} joins the party.")
    store.push_event("toast", {"text": f"{comp.get('name')} joined the party", "icon": "tpl:ic_star"})
    return {"ok": True, "id": comp["id"]}


@tool
def remove_companion(companion_id: str, reason: str = "") -> dict:
    """Remove a companion (left, died...)."""
    with _campaign() as c:
        c["party"] = [p for p in c["party"] if p["id"] != companion_id]
        _log(c, "system", f"{companion_id} left the party. {reason}")
    store.touch()
    return {"ok": True}


@tool
def finish_setup(start_note: str = "") -> dict:
    """End character creation: status -> active, start run #N, clear setup screen. Call after dm_notes has the scenario."""
    with _campaign() as c:
        c["status"] = "active"
        ch = c["character"]
        for r in _theme(c)["resources"]:
            ch["resources"].setdefault(r["key"], {"cur": 10, "max": 10})
        c["runs"].append({"n": len(c["runs"]) + 1, "character": ch.get("name"), "started": now_iso(),
                          "turn_started": c["turn"], "ended": None, "cause": None})
        c["scene"]["mode"] = "scene"; c["scene"]["showcase"] = None
        _log(c, "system", start_note or f"Run {len(c['runs'])} begins: {ch.get('name')}.")
        _snapshot(c)
    store.set_loading(done=True)
    store.push_event("title", {"text": c["name"], "sub": f"Run {len(c['runs'])} - {c['character'].get('name')}"})
    return {"ok": True, "run": len(c["runs"])}


@tool
def dm_notes(set: dict | None = None, add_note: str = "", add_secret: str = "", add_plan: str = "") -> dict:
    """Read/update the hidden DM section of the campaign file (never shown in the UI).
    set: deep-merge into dm (e.g. {"scenario":{"premise":..,"acts":[..],"villain":..,"twist":..}}).
    add_note / add_secret / add_plan append to lists. Returns the whole dm section."""
    with _campaign() as c:
        dm = c.setdefault("dm", {})
        if set:
            _deep_merge(dm, set)
        for key, val in (("notes", add_note), ("secrets", add_secret), ("plans", add_plan)):
            if val:
                dm.setdefault(key, []).append({"turn": c["turn"], "text": val})
    return {"dm": dm}


@tool
def get_state(include_dm: bool = True, full: bool = False) -> dict:
    """Current campaign state. full=False gives a compact summary + scene; full=True the whole file (minus snapshots)."""
    c = _load()
    if full:
        out = {k: v for k, v in c.items() if k != "snapshots"}
        if not include_dm:
            out.pop("dm", None)
        return out
    out = {"summary": _summary(c), "character": c["character"], "party": c["party"], "scene": c["scene"],
           "combat": c["combat"], "quests": c["quests"], "world": {k: v for k, v in c["world"].items() if k != "maps"}}
    if include_dm:
        out["dm"] = c.get("dm")
    return out


# =====================================================================
# ASSETS / LIBRARY
# =====================================================================
@tool
def find_assets(query: str = "", category: str = "", tags: list | None = None, limit: int = 30) -> dict:
    """Search the active theme's library AND the shared template library before creating anything.
    category: character|portrait|creature|tile|object|item|icon|backdrop. Results give 'ref' usable in recipes
    ('tpl:<name>' for shared templates, bare id for theme assets). Templates list their params."""
    slug = None
    with contextlib.suppress(DMError):
        slug = _load()["theme"]
    return {"theme": slug, "results": assets.find(slug, query, category or None, tags, True, limit)}


@tool
def create_asset(id: str, category: str, desc: str, tags: list, template: str = "", params: dict | None = None,
                 colors: dict | None = None, rows: list | None = None, legend: dict | None = None,
                 layer: int | None = None, outline: bool = True) -> dict:
    """Create a NEW asset in the active theme library - only when find_assets has nothing suitable.
    Either (a) freeze a template variant: template='tpl:cr_beast', params={...}, colors={"primary":"#553"}; or
    (b) draw a bespoke pixel grid: rows=["..oo..", ...] using the standard legend chars:
      o outline | s/S/c skin(base/dark/light) | h/H/j hair | t/T/u top | a/A/v accent | l/L legs | b/B boots |
      m/M/n metal | w/W/i wood | g/G/f glow | e eyes | y white | r mouth | x shadow(translucent) |
      p/P/q primary | k/K/z secondary | d/D detail | '.' transparent. Custom chars via legend {"Q":"#ff00ff"}.
    Sizes: character layers 16x24, portrait layers 32x32, tiles 16x16, objects 16x16/16x24, backdrops 96x54, icons 14x14.
    layer: z-order (back 5, body 10, legs 20, boots 25, top 30, face 40, beard 45, hair 50, hat 60, held 70)."""
    slug = _load()["theme"]
    aid = assets.register_asset(slug, id, category, rows=rows, legend=legend, template=template or None,
                                params={**(params or {}), "outline": outline} if rows else params,
                                colors=colors, tags=tags, desc=desc, layer=layer)
    store.touch()
    return {"ok": True, "ref": aid, "theme": slug}


@tool
def showcase(title: str = "", items: list | None = None, columns: int = 4) -> dict:
    """Show a numbered gallery overlay in the UI so the player can pick (e.g. hair styles, archetypes, loot).
    items: [{"label":"1. Short","sprite":recipe} | {"label":..,"portrait":recipe,"expression":"happy"} |
            {"label":..,"part":"tpl:ic_star"} | {"label":..,"text":"..."}]. Call with no items to close."""
    with _campaign() as c:
        c["scene"]["showcase"] = {"title": title, "items": items or [], "columns": columns} if items else None
    store.push_event("showcase", {"open": bool(items)})
    return {"ok": True}


# ---------------- NPCs / lore / tables ----------------
def _lib_find(sub, query, ext="json"):
    slug = _load()["theme"]
    d = assets.theme_dir(slug) / sub
    q = [t for t in (query or "").lower().split() if t]
    out = []
    for p in sorted(d.glob(f"*.{ext}")):
        text = p.read_text(encoding="utf-8")
        s = sum(1 for t in q if t in text.lower()) if q else 1
        if s:
            out.append((s, p))
    out.sort(key=lambda t: -t[0])
    return slug, [p for _, p in out]


@tool
def find_npcs(query: str = "") -> dict:
    """Search reusable NPC templates in the theme library (name/role/tags/personality)."""
    _, paths = _lib_find("npcs", query)
    res = []
    for p in paths[:30]:
        n = store.read_json(p, {})
        res.append({k: n.get(k) for k in ("id", "name", "role", "desc", "tags", "personality")})
    return {"results": res}


@tool
def create_npc(id: str, name: str, role: str, desc: str, personality: str = "", sprite: dict | None = None,
               portrait: dict | None = None, stats: dict | None = None, tags: list | None = None,
               voice: dict | None = None) -> dict:
    """Save a reusable NPC template in the theme library (appearance + personality + stats + voice). Campaign-specific
    facts (met, killed, attitude) go in the campaign via npc_state, not here.
    voice: {"voice":"en-GB-RyanNeural","rate":"-5%","pitch":"-3Hz","fx":"radio|robot|echo|deep|"} (see list_voices)."""
    slug = _load()["theme"]
    nid = slugify(id).replace("-", "_")
    n = {"id": nid, "name": name, "role": role, "desc": desc, "personality": personality, "voice": voice,
         "sprite": sprite or {"layers": []}, "portrait": portrait or {"layers": []}, "stats": stats or {},
         "tags": tags or [], "created": now_iso()}
    if voice:
        n["voice"] = tts.norm_voice({"voice": voice} if isinstance(voice, str) else voice)
    store.write_json(assets.theme_dir(slug) / "npcs" / f"{nid}.json", n)
    return {"ok": True, "id": nid}


@tool
def get_npc(id: str) -> dict:
    """Load a full NPC template."""
    slug = _load()["theme"]
    n = store.read_json(assets.theme_dir(slug) / "npcs" / f"{id}.json", None)
    if not n:
        raise DMError("npc not found")
    return n


@tool
def npc_state(id: str, changes: dict) -> dict:
    """Campaign-specific NPC facts (attitude, met, alive, notes, location). Deep-merged into world.npcs[id]."""
    with _campaign() as c:
        st = c["world"]["npcs"].setdefault(id, {"met": True})
        _deep_merge(st, changes)
    return {"ok": True, "npc": st}


@tool
def find_lore(query: str = "") -> dict:
    """Search the theme's lore notes (places, factions, history). Returns titles + first lines."""
    _, paths = _lib_find("lore", query, "md")
    return {"results": [{"id": p.stem, "preview": p.read_text(encoding="utf-8")[:300]} for p in paths[:20]]}


@tool
def read_lore(id: str) -> dict:
    """Read one lore note."""
    slug = _load()["theme"]
    p = assets.theme_dir(slug) / "lore" / f"{id}.md"
    if not p.exists():
        raise DMError("lore not found")
    return {"id": id, "text": p.read_text(encoding="utf-8")}


@tool
def write_lore(id: str, title: str, text: str, tags: list | None = None) -> dict:
    """Create/replace a reusable lore note in the theme (world facts that stay true across campaigns)."""
    slug = _load()["theme"]
    lid = slugify(id)
    body = f"# {title}\n\ntags: {', '.join(tags or [])}\n\n{text}\n"
    store.write_text(assets.theme_dir(slug) / "lore" / f"{lid}.md", body)
    return {"ok": True, "id": lid}


@tool
def table(action: str, id: str = "", entries: list | None = None, count: int = 1) -> dict:
    """Random tables stored in the theme (loot, encounters, rumours, room contents).
    action: 'list' | 'save' (entries=[{"w":3,"text":"2 rats","data":{...}}, ...] or plain strings) | 'roll' | 'show'."""
    slug = _load()["theme"]
    d = assets.theme_dir(slug) / "tables"
    if action == "list":
        return {"tables": [p.stem for p in d.glob("*.json")]}
    p = d / f"{slugify(id)}.json"
    if action == "save":
        ents = [e if isinstance(e, dict) else {"w": 1, "text": str(e)} for e in (entries or [])]
        store.write_json(p, {"id": slugify(id), "entries": ents})
        return {"ok": True}
    t = store.read_json(p, None)
    if not t:
        raise DMError("table not found")
    if action == "show":
        return t
    ents = t["entries"]
    picks = random.choices(ents, weights=[e.get("w", 1) for e in ents], k=max(1, count))
    return {"results": picks}


# =====================================================================
# MAPS
# =====================================================================
@tool
def find_maps(query: str = "") -> dict:
    """Search map layouts already in the theme library (reuse before creating)."""
    _, paths = _lib_find("maps", query)
    res = []
    for p in paths:
        m = store.read_json(p, {})
        res.append({"id": m.get("id"), "name": m.get("name"), "desc": m.get("desc"), "tags": m.get("tags"),
                    "size": [m.get("w"), m.get("h")], "spawns": m.get("spawns")})
    return {"results": res}


@tool
def create_map(id: str, name: str, rows: list, legend: dict, desc: str = "", tags: list | None = None,
               spawns: dict | None = None, objects: list | None = None, backdrop: dict | None = None) -> dict:
    """Save a small explorable map in the theme library (reused by later campaigns). Keep it ~12-24 x 8-16.
    rows: list of equal-length strings, one char per tile.
    legend: {char: {"tile":"tpl:tile_floor_stone","colors":{"primary":"#555"},"solid":false,"name":"stone floor",
                    "under":"<char drawn beneath, for trees/doors on grass>"}}.
    spawns: {"start":[x,y],"exit":[x,y]}. objects: static decor [{"x","y","part":"tpl:obj_torch"} | {"x","y","sprite":recipe}].
    backdrop: scene-mode backdrop recipe to use when talking inside this map."""
    slug = _load()["theme"]
    w = max(len(r) for r in rows)
    rows = [r.ljust(w, rows[0][0]) for r in rows]
    missing = sorted({ch for r in rows for ch in r if ch not in legend})
    if missing:
        raise DMError(f"legend missing chars: {missing}")
    mid = slugify(id).replace("-", "_")
    m = {"id": mid, "name": name, "desc": desc, "tags": tags or [], "w": w, "h": len(rows), "rows": rows,
         "legend": legend, "spawns": spawns or {}, "objects": objects or [], "backdrop": backdrop, "created": now_iso()}
    store.write_json(assets.map_path(slug, mid), m)
    return {"ok": True, "id": mid, "size": [w, len(rows)]}


def _reveal(c, mid, cells):
    st = c["world"]["maps"].setdefault(mid, {"explored": [], "markers": [], "visits": 0})
    ex = set(tuple(p) for p in st["explored"])
    ex.update(cells)
    st["explored"] = sorted([list(p) for p in ex])


def _circle(x, y, r, w, h):
    return [(xx, yy) for yy in range(max(0, y - r), min(h, y + r + 1))
            for xx in range(max(0, x - r), min(w, x + r + 1)) if (xx - x) ** 2 + (yy - y) ** 2 <= r * r + r]


@tool
def load_map(map_id: str, spawn: str = "start", pos: list | None = None, reveal_radius: int = 3,
             keep_entities: bool = False, title: str = "") -> dict:
    """Switch the stage to a map (mode 'map') and place the player token. pos=[x,y] overrides spawn."""
    with _campaign() as c:
        m = assets.load_map(c["theme"], map_id)
        if not m:
            raise DMError(f"map '{map_id}' not in theme library; find_maps / create_map")
        p = pos or m.get("spawns", {}).get(spawn) or [m["w"] // 2, m["h"] // 2]
        c["world"]["map"] = map_id; c["world"]["pos"] = list(p)
        c["world"]["location"] = title or m["name"]
        st = c["world"]["maps"].setdefault(map_id, {"explored": [], "markers": [], "visits": 0})
        st["visits"] += 1
        _reveal(c, map_id, _circle(p[0], p[1], reveal_radius, m["w"], m["h"]))
        c["scene"]["mode"] = "map"; c["scene"]["title"] = title or m["name"]
        if not keep_entities:
            c["scene"]["entities"] = []
        _log(c, "system", f"Entered {m['name']}.")
    store.push_event("scene", {"mode": "map", "title": title or m["name"]})
    return {"ok": True, "map": {k: m[k] for k in ("id", "name", "w", "h", "rows")}, "pos": p,
            "legend": {k: (v.get("name") if isinstance(v, dict) else v) for k, v in m["legend"].items()}}


@tool
def reveal(x: int = -1, y: int = -1, radius: int = 2, cells: list | None = None, all: bool = False) -> dict:
    """Clear fog of war on the current map: circle at (x,y), explicit cells [[x,y],...], or all=True."""
    with _campaign() as c:
        mid = c["world"]["map"]
        m = assets.load_map(c["theme"], mid)
        if all:
            pts = [(xx, yy) for yy in range(m["h"]) for xx in range(m["w"])]
        elif cells:
            pts = [tuple(p) for p in cells]
        else:
            pts = _circle(x, y, radius, m["w"], m["h"])
        _reveal(c, mid, pts)
    store.touch()
    return {"ok": True}


@tool
def move_player(x: int, y: int, reveal_radius: int = 3) -> dict:
    """Move the player token on the current map and reveal around it. Returns the tile under the player."""
    with _campaign() as c:
        mid = c["world"]["map"]
        m = assets.load_map(c["theme"], mid)
        if not m:
            raise DMError("no map loaded")
        x = max(0, min(m["w"] - 1, x)); y = max(0, min(m["h"] - 1, y))
        c["world"]["pos"] = [x, y]
        if reveal_radius > 0:
            _reveal(c, mid, _circle(x, y, reveal_radius, m["w"], m["h"]))
        ch = m["rows"][y][x]; ent = m["legend"].get(ch, {})
    store.push_event("move", {"id": "player", "x": x, "y": y})
    return {"pos": [x, y], "tile": ent.get("name") if isinstance(ent, dict) else ent,
            "solid": isinstance(ent, dict) and ent.get("solid", False)}


@tool
def marker(action: str, id: str, x: int = 0, y: int = 0, icon: str = "tpl:ic_pin", label: str = "") -> dict:
    """Add ('add') or remove ('remove') a labelled marker/icon on the current map (campaign-specific)."""
    with _campaign() as c:
        st = c["world"]["maps"].setdefault(c["world"]["map"], {"explored": [], "markers": [], "visits": 0})
        st["markers"] = [mk for mk in st["markers"] if mk["id"] != id]
        if action == "add":
            st["markers"].append({"id": id, "x": x, "y": y, "icon": icon, "label": label})
    store.touch()
    return {"ok": True}


# =====================================================================
# SCENE / NARRATIVE
# =====================================================================
@tool
def set_scene(mode: str = "scene", title: str = "", backdrop: dict | None = None, location: str = "",
              time: str = "", weather: str = "", clear_entities: bool = False, mood: str = "") -> dict:
    """Set the stage. mode: 'scene' (VN backdrop + characters), 'map' (tile map), 'title' (big title card).
    backdrop: recipe e.g. {"layers":[{"part":"tpl:bd_interior","params":{"window":true}}],"colors":{"primary":"#4a3a38"}}.
    time: e.g. 'dawn','day','dusk','night'; weather: 'clear','rain','fog','snow','storm'. mood tints the stage:
    'warm','cold','eerie','danger','calm','dark'."""
    with _campaign() as c:
        s = c["scene"]
        s["mode"] = mode
        if title:
            s["title"] = title
        if backdrop is not None:
            s["backdrop"] = backdrop
        if mood:
            s["mood"] = mood
        if clear_entities:
            s["entities"] = []
        w = c["world"]
        if location:
            w["location"] = location
        if time:
            w["time"] = time
        if weather:
            w["weather"] = weather
    store.push_event("scene", {"mode": mode, "title": title})
    return {"ok": True}


def _voice_of(c, speaker_id=None, actor=None, npc=None, name=""):
    """Resolve a speaking voice: explicit actor/npc voice -> npc template -> deterministic auto voice."""
    theme = assets.load_theme(c["theme"]) or {}
    narr = tts.norm_voice((theme.get("voices") or {}).get("narrator")) or dict(tts.DEFAULT_NARRATOR)
    if speaker_id == "narrator":
        return narr
    for src in (actor, npc):
        if src and src.get("voice"):
            return tts.norm_voice(src["voice"])
    if actor and actor.get("npc"):
        n = store.read_json(assets.theme_dir(c["theme"]) / "npcs" / f"{actor['npc']}.json", None)
        if n and n.get("voice"):
            return tts.norm_voice(n["voice"])
    return tts.auto_voice(name or speaker_id or "?", exclude=(narr["voice"],),
                          gender=(actor or npc or {}).get("voice_gender"))


@tool
def narrate(text: str, style: str = "normal") -> dict:
    """Show narration in the dialogue box (typewriter, voiced by the narrator when voiceover is on).
    style: normal | dramatic | whisper | system. Long text is paged automatically in the browser."""
    with _campaign() as c:
        v = _voice_of(c, "narrator")
        c["scene"]["dialogue"] = {"speaker": None, "text": text, "style": style}
        _log(c, "narration", text, style=style)
    store.push_event("narrate", {"text": text, "style": style, "voice": v if style != "system" else None})
    store.set_dm_status("thinking")
    return {"ok": True}


@tool
def say(speaker: str, text: str, expression: str = "neutral", name: str = "") -> dict:
    """A character speaks in the dialogue box with their portrait and voice. speaker: companion id, scene entity id,
    or NPC template id ('player' only to echo the player's own words - never voiced). expression: neutral|happy|laugh|
    angry|sad|surprised|smirk|hurt|calm|determined|scared."""
    with _campaign() as c:
        portrait, disp, actor, npc = None, name or speaker, None, None
        try:
            actor, _ = _find_actor(c, speaker)
            portrait = actor.get("portrait"); disp = name or actor.get("name") or speaker
            if speaker not in ("player",):
                actor["expression"] = expression
        except DMError:
            npc = store.read_json(assets.theme_dir(c["theme"]) / "npcs" / f"{speaker}.json", None)
            if npc:
                portrait = npc.get("portrait"); disp = name or npc.get("name")
        voice = None if speaker in ("player", "me", "pc") else _voice_of(c, speaker, actor, npc, disp)
        dlg = {"speaker": disp, "speaker_id": speaker, "portrait": portrait, "text": text,
               "expression": expression, "style": "speech"}
        c["scene"]["dialogue"] = dlg
        _log(c, "speech", text, speaker=disp)
    store.push_event("say", {**dlg, "voice": voice})
    store.set_dm_status("thinking")
    return {"ok": True, "voice": voice}


@tool
def spawn(id: str, name: str = "", sprite: dict | None = None, portrait: dict | None = None, npc: str = "",
          x: int | None = None, y: int | None = None, slot: float | None = None, side: str = "neutral",
          hp: int | None = None, flip: bool = False, scale: float = 1.0, note: str = "",
          voice: dict | None = None) -> dict:
    """Put a character/creature/object on stage. Look from sprite recipe or an NPC template id (npc=).
    Map mode: tile x,y. Scene mode: slot = horizontal position 0-100 (%). side: ally|enemy|neutral|object.
    hp shows a health bar. scale: 1 normal, 2 = big (bosses)."""
    with _campaign() as c:
        e = {"id": slugify(id).replace("-", "_"), "name": name or id, "side": side, "flip": flip, "scale": scale,
             "expression": "neutral", "conditions": [], "note": note}
        if npc:
            n = store.read_json(assets.theme_dir(c["theme"]) / "npcs" / f"{npc}.json", None)
            if not n:
                raise DMError(f"npc template '{npc}' not found")
            e.update({"npc": npc, "name": name or n["name"], "sprite": n.get("sprite"), "portrait": n.get("portrait")})
        if sprite:
            e["sprite"] = sprite if isinstance(sprite, dict) else {"layers": sprite}
        if portrait:
            e["portrait"] = portrait
        if voice:
            e["voice"] = tts.norm_voice(voice)
        if x is not None:
            e["x"], e["y"] = x, y
        e["slot"] = slot if slot is not None else 50
        if hp is not None:
            e["hp"] = {"cur": hp, "max": hp}
        c["scene"]["entities"] = [o for o in c["scene"]["entities"] if o["id"] != e["id"]] + [e]
    store.push_event("spawn", {"id": e["id"]})
    return {"ok": True, "id": e["id"]}


@tool
def update_entity(id: str, changes: dict) -> dict:
    """Change a stage entity: {"x":..,"y":..} move on map, {"slot":30} move in scene, {"expression":"angry"},
    {"flip":true}, {"hidden":true}, {"hp":{"cur":3}}, {"sprite":{...}}, {"side":"enemy"}, {"name":..}."""
    with _campaign() as c:
        e, _ = _find_actor(c, id)
        _deep_merge(e, changes)
    store.push_event("move" if ("x" in changes or "slot" in changes) else "state", {"id": id})
    return {"ok": True, "entity": e}


@tool
def remove_entity(id: str, how: str = "fade") -> dict:
    """Remove an entity from the stage (how: fade|defeated)."""
    with _campaign() as c:
        c["scene"]["entities"] = [o for o in c["scene"]["entities"] if o["id"] != id]
    store.push_event("remove", {"id": id, "how": how})
    return {"ok": True}


@tool
def effect(kind: str, text: str = "", target: str = "", color: str = "") -> dict:
    """Visual flourish. kind: shake | flash | float (number/text over target) | title (big centred card) |
    toast (small notification) | fade | levelup | heal | damage."""
    ev = {"kind": kind, "text": text, "target": target, "color": color}
    store.push_event("effect", ev)
    return {"ok": True}


# =====================================================================
# PARTY / STATS
# =====================================================================
@tool
def update_stats(target: str = "player", delta: dict | None = None, set: dict | None = None,
                 max: dict | None = None, reason: str = "") -> dict:
    """Change resources/stats. delta: {"hp":-5,"xp":50,"currency":-10,"str":1}. set: absolute values.
    max: change resource maximums {"hp":20}. Resources clamp to 0..max. target: player | companion id | entity id."""
    changes = []
    with _campaign() as c:
        a, kind = _find_actor(c, target)
        res = a.setdefault("resources", {}) if kind != "entity" else None
        for k, v in (max or {}).items():
            if kind == "entity":
                a.setdefault(k, {"cur": v, "max": v})["max"] = v
            else:
                r = res.setdefault(k, {"cur": v, "max": v}); r["max"] = v; r["cur"] = min(r["cur"], v)
        for k, v in (delta or {}).items():
            if kind == "entity" and k in a and isinstance(a[k], dict):
                _clamp(a[k], v)
            elif res is not None and k in res:
                _clamp(res[k], v)
            elif k in a.get("stats", {}):
                a["stats"][k] += v
            elif k in ("xp", "currency", "level"):
                a[k] = a.get(k, 0) + v
            else:
                raise DMError(f"unknown stat/resource '{k}'")
            changes.append((k, v))
        for k, v in (set or {}).items():
            if res is not None and k in res:
                res[k]["cur"] = v
            elif k in a.get("stats", {}):
                a["stats"][k] = v
            else:
                a[k] = v
        if changes:
            _log(c, "stat", f"{a.get('name', target)}: " + ", ".join(f"{k} {v:+}" for k, v in changes) + (f" ({reason})" if reason else ""))
    for k, v in changes:
        if k in ("hp", "health", "integrity") or (res and k in res):
            store.push_event("effect", {"kind": "damage" if v < 0 else "heal", "text": f"{v:+}", "target": target, "stat": k})
        elif k == "xp":
            store.push_event("effect", {"kind": "float", "text": f"+{v} XP", "target": target, "color": "#ffe04a"})
    if not changes:
        store.touch()
    return {"ok": True, "target": target, "resources": a.get("resources", a.get("hp")), "stats": a.get("stats")}


def _clamp(r, v):
    r["cur"] = max(0, min(r["max"], r["cur"] + v))


@tool
def condition(target: str = "player", add: list | None = None, remove: list | None = None) -> dict:
    """Add/remove conditions (poisoned, burning, stunned, blessed, bleeding, frightened, hidden...; theme may add more)."""
    with _campaign() as c:
        a, _ = _find_actor(c, target)
        cur = a.setdefault("conditions", [])
        for x in add or []:
            if x not in cur:
                cur.append(x)
        a["conditions"] = [x for x in cur if x not in (remove or [])]
        if add or remove:
            _log(c, "stat", f"{a.get('name', target)} conditions: +{add or []} -{remove or []}")
    for x in add or []:
        store.push_event("effect", {"kind": "float", "text": x, "target": target, "color": "#c07aff"})
    store.touch()
    return {"ok": True, "conditions": a["conditions"]}


@tool
def inventory(action: str, item: dict, target: str = "player") -> dict:
    """action add | remove | update. item: {"id":"healing_potion","name":"Healing Potion","qty":1,
    "icon":"tpl:item_potion","colors":{"glow":"#e04a5a"},"desc":"Heals 2d4+2","equipped":false,"tags":[]}.
    remove with qty decrements; qty 0 deletes."""
    with _campaign() as c:
        a, _ = _find_actor(c, target)
        inv = a.setdefault("inventory", [])
        iid = slugify(item.get("id") or item.get("name")).replace("-", "_")
        ex = next((i for i in inv if i["id"] == iid), None)
        if action == "add":
            if ex:
                ex["qty"] = ex.get("qty", 1) + item.get("qty", 1)
            else:
                inv.append({"qty": 1, "icon": "tpl:item_bag", **item, "id": iid})
            _log(c, "item", f"+ {item.get('qty', 1)}x {item.get('name', iid)}")
            store.push_event("effect", {"kind": "toast", "text": f"+ {item.get('name', iid)}", "icon": item.get("icon")})
        elif action == "remove":
            if not ex:
                raise DMError(f"no item {iid}")
            ex["qty"] = ex.get("qty", 1) - item.get("qty", 1)
            if ex["qty"] <= 0:
                inv.remove(ex)
            _log(c, "item", f"- {item.get('qty', 1)}x {ex.get('name', iid)}")
            store.touch()
        elif action == "update":
            if not ex:
                raise DMError(f"no item {iid}")
            _deep_merge(ex, {k: v for k, v in item.items() if k != "id"}); store.touch()
    return {"ok": True, "inventory": inv}


@tool
def quest(id: str, title: str = "", status: str = "active", desc: str = "", objectives: list | None = None) -> dict:
    """Create/update a quest. status: active | done | failed | hidden. objectives: [{"text":..,"done":false}]."""
    with _campaign() as c:
        qid = slugify(id)
        q = next((x for x in c["quests"] if x["id"] == qid), None)
        new = q is None
        if new:
            q = {"id": qid, "title": title or id, "status": status, "desc": desc, "objectives": objectives or [],
                 "turn": c["turn"]}
            c["quests"].append(q)
        else:
            if title: q["title"] = title
            if desc: q["desc"] = desc
            if objectives is not None: q["objectives"] = objectives
            q["status"] = status
    if status != "hidden":
        label = {"active": "New quest" if new else "Quest updated", "done": "Quest complete", "failed": "Quest failed"}.get(status, "Quest")
        store.push_event("effect", {"kind": "toast", "text": f"{label}: {q['title']}", "icon": "tpl:ic_bang"})
    return {"ok": True, "quest": q}


@tool
def journal(text: str, title: str = "") -> dict:
    """Add a player-visible journal entry (clues, discoveries, recaps)."""
    with _campaign() as c:
        c["journal"].append({"turn": c["turn"], "title": title, "text": text, "t": now_iso()})
    store.push_event("effect", {"kind": "toast", "text": "Journal updated", "icon": "tpl:ic_scroll"})
    return {"ok": True}


# =====================================================================
# DICE / COMBAT
# =====================================================================
@tool
def roll(expr: str = "1d20", reason: str = "", dc: int | None = None, mode: str = "", who: str = "player",
         hidden: bool = False) -> dict:
    """Roll dice with real randomness, animate it on screen and log it (so the DM can't fudge).
    expr: '1d20+3', '2d6+1d4-1', '4d6kh3', 'd100'. mode: adv | dis (d20 advantage/disadvantage).
    dc: difficulty -> success true/false (nat 20 / nat 1 flagged). hidden: DM-secret roll (not shown)."""
    r = dice.roll(expr, mode or None)
    r.update({"reason": reason, "dc": dc, "who": who, "mode": mode, "hidden": hidden})
    if dc is not None:
        r["success"] = r["total"] >= dc
    with _campaign() as c:
        r["turn"] = c["turn"]
        c["rolls"].append(r); c["rolls"] = c["rolls"][-200:]
        if not hidden:
            res = f" vs DC {dc}: {'SUCCESS' if r.get('success') else 'FAIL'}" if dc is not None else ""
            _log(c, "roll", f"{reason or expr}: {r['total']}{res}", who=who)
    if not hidden:
        store.push_event("roll", r)
    return r


@tool
def start_combat(participants: list, initiative: dict | None = None) -> dict:
    """Begin an encounter. participants: ids ('player', companion ids, entity ids). Initiative is rolled
    (d20 + mod) unless initiative={id: value} is given. mods via initiative={"mods":{"goblin":2}}."""
    init = dict(initiative or {})
    mods = init.pop("mods", {})
    order = []
    with _campaign() as c:
        for pid in participants:
            if pid in init:
                v = init[pid]
            else:
                mod = mods.get(pid)
                if mod is None and pid == "player":
                    mod = (c["character"].get("stats", {}).get("dex", 10) - 10) // 2
                v = dice.roll(f"1d20{int(mod or 0):+d}")["total"]
            try:
                a, _ = _find_actor(c, pid); nm = a.get("name", pid)
            except DMError:
                nm = pid
            order.append({"id": pid, "name": nm, "init": v})
        order.sort(key=lambda o: -o["init"])
        c["combat"] = {"active": True, "round": 1, "order": order, "turn_index": 0}
        _log(c, "system", "Combat! Initiative: " + ", ".join(f"{o['name']} {o['init']}" for o in order))
    store.push_event("effect", {"kind": "title", "text": "Combat!"})
    store.push_event("combat", {"order": order})
    return {"order": order, "current": order[0]}


@tool
def next_turn() -> dict:
    """Advance the combat turn marker (increments round when wrapping)."""
    with _campaign() as c:
        cb = c["combat"]
        if not cb.get("active"):
            raise DMError("no combat")
        cb["turn_index"] += 1
        if cb["turn_index"] >= len(cb["order"]):
            cb["turn_index"] = 0; cb["round"] += 1
        cur = cb["order"][cb["turn_index"]]
    store.push_event("combat", {"current": cur})
    return {"round": cb["round"], "current": cur}


@tool
def end_combat(outcome: str = "victory") -> dict:
    """End the encounter (outcome: victory | defeat | fled | truce)."""
    with _campaign() as c:
        c["combat"] = {"active": False, "round": 0, "order": [], "turn_index": 0}
        _log(c, "system", f"Combat ended: {outcome}")
    store.push_event("effect", {"kind": "title", "text": outcome.capitalize()})
    return {"ok": True}


# =====================================================================
# FLOW / SAVES / ROGUELIKE
# =====================================================================
def _snapshot(c):
    snap = copy.deepcopy({k: v for k, v in c.items() if k != "snapshots"})
    snap["log"] = snap.get("log", [])[-60:]
    snaps = [s for s in c.get("snapshots", []) if s.get("turn") != c["turn"]]
    snaps.append(snap)
    c["snapshots"] = snaps[-store.config()["snapshots_kept"]:]


@tool
def end_turn(summary: str) -> dict:
    """Call after each resolved player action: logs the summary, increments the turn and stores a rollback
    snapshot of the new turn's starting state."""
    with _campaign() as c:
        _log(c, "turn", summary)
        c["turn"] += 1
        _snapshot(c)
    store.touch()
    return {"turn": c["turn"]}


@tool
def rollback(steps: int = 1) -> dict:
    """Undo the last `steps` turns: restores the state at the START of turn (current - steps).
    steps=0 discards changes made during the current, unfinished turn."""
    c = _load()
    want = c["turn"] - steps
    snaps = c.get("snapshots", [])
    idx = next((i for i, s in enumerate(snaps) if s.get("turn") == want), None)
    if idx is None:
        raise DMError(f"no snapshot for turn {want}; available turns: {[s.get('turn') for s in snaps]}")
    target = copy.deepcopy(snaps[idx])
    target["snapshots"] = snaps[:idx + 1]
    _log(target, "system", f"Rolled back to the start of turn {want}.")
    _save(target)
    store.push_event("reload", {})
    return {"ok": True, "turn": target["turn"]}


@tool
def end_run(cause: str, legacy: list | None = None, epilogue: str = "") -> dict:
    """Roguelike death/retirement of the current character. Records the run, stores legacy unlocks that carry over to
    the next character in THIS campaign, resets the character and sets status 'setup' for a new character.
    legacy: e.g. ["+1 starting potion", "Ghost of <name> can appear as a guide"]."""
    with _campaign() as c:
        ch = c["character"]
        if c["runs"]:
            c["runs"][-1].update({"ended": now_iso(), "cause": cause, "turns": c["turn"] - c["runs"][-1].get("turn_started", 0),
                                  "level": ch.get("level"), "final": copy.deepcopy(ch), "epilogue": epilogue})
        c["legacy"] += legacy or []
        c["status"] = "setup"
        c["character"] = _new_character()
        c["scene"] = {"mode": "setup", "title": "", "backdrop": None, "entities": [], "dialogue": None, "showcase": None}
        c["combat"] = {"active": False, "round": 0, "order": [], "turn_index": 0}
        _log(c, "system", f"{ch.get('name')} has fallen: {cause}")
    store.push_event("effect", {"kind": "title", "text": "You have fallen", "sub": cause})
    return {"ok": True, "runs": len(c["runs"]), "legacy": c["legacy"]}


@tool
def end_campaign(epilogue: str, outcome: str = "complete") -> dict:
    """Close the campaign (outcome: complete | abandoned)."""
    with _campaign() as c:
        c["status"] = outcome; c["epilogue"] = epilogue
        if c["runs"] and not c["runs"][-1].get("ended"):
            c["runs"][-1].update({"ended": now_iso(), "cause": outcome})
    store.push_event("effect", {"kind": "title", "text": "The End", "sub": c["name"]})
    return {"ok": True}



# =====================================================================
# VOICES
# =====================================================================
@tool
def list_voices(accent: str = "", gender: str = "") -> dict:
    """Available neural voices for voiceover (English). Filter by accent (US UK AU IE IN ZA NG KE SG CA NZ HK PH)
    or gender (m/f). Tune with rate ('-10%'..'+20%'), pitch ('-8Hz'..'+8Hz') and fx (radio robot echo deep)."""
    out = [{"voice": v, "gender": g, "accent": a, "feel": d} for v, g, a, d in tts.VOICES
           if (not accent or a.lower() == accent.lower()) and (not gender or g == gender.lower()[:1])]
    return {"voices": out, "fx": tts.FX}


@tool
def set_voice(target: str, voice: str, rate: str = "+0%", pitch: str = "+0Hz", fx: str = "") -> dict:
    """Assign a voice. target: 'narrator' (stored in the theme, reused by all campaigns), an NPC template id (stored in
    the theme), or a companion/scene-entity id (stored in the campaign). Unassigned speakers get a stable auto voice."""
    v = tts.norm_voice({"voice": voice, "rate": rate, "pitch": pitch, "fx": fx})
    c = _load()
    if target == "narrator":
        p = assets.theme_dir(c["theme"]) / "theme.json"; t = store.read_json(p, {})
        t.setdefault("voices", {})["narrator"] = v; store.write_json(p, t)
        return {"ok": True, "stored": "theme", "voice": v}
    with _campaign() as c2:
        try:
            a, _ = _find_actor(c2, target)
            a["voice"] = v
            return {"ok": True, "stored": "campaign", "voice": v}
        except DMError:
            pass
    p = assets.theme_dir(c["theme"]) / "npcs" / f"{target}.json"
    n = store.read_json(p, None)
    if not n:
        raise DMError(f"no narrator/actor/npc '{target}'")
    n["voice"] = v; store.write_json(p, n)
    return {"ok": True, "stored": "npc template", "voice": v}


# =====================================================================
# BROWSER INPUT (Speak / Do / DM)
# =====================================================================
def _fmt_action(a, pname):
    if a["type"] == "speak":
        m = a.get("manner") or "normal"
        who = f" to {a['target']}" if a.get("target") else ""
        return f"{pname} ({m}){who}: \"{a['text']}\""
    if a["type"] == "do":
        return f"{pname} does: {a['text']}"
    return f"[to DM] {a['text']}"


SYSTEM_REQ = ("build_theme", "new_game", "resume")


def _take(limit=None):
    cid = store.runtime().get("active")
    with store.file_lock("inbox"):
        ib = store.inbox()
        pend = [a for a in ib["actions"] if a.get("status") == "pending"
                and (a.get("type") in SYSTEM_REQ or (cid and a.get("campaign") == cid))]
        take = pend[:limit] if limit else pend
        now = now_iso()
        for a in take:
            a["status"] = "received"; a["received_at"] = now
        if take:
            store.write_json(store.INBOX, ib)
    if not take:
        return []
    sysreq = [a for a in take if a["type"] in SYSTEM_REQ]
    for a in sysreq:
        a["display"] = f"[menu request] {a['type']}"
    take_story = [a for a in take if a["type"] not in SYSTEM_REQ]
    if not take_story:
        store.set_dm_status("thinking", last_action_at=_time.time(), idle_since=None)
        return take
    with _campaign() as c:
        ch = c["character"]; pname = ch.get("name") or "You"
        for a in take_story:
            a["display"] = _fmt_action(a, pname)
            if a["type"] == "dm":
                c.setdefault("ooc", []).append({"from": "player", "text": a["text"], "t": now_iso()})
                continue
            _log(c, "action", a["display"], action=a["type"])
            if a["type"] == "do":
                c["scene"]["dialogue"] = {"speaker": None, "text": "\u25b6 " + a["text"], "style": "act", "act": True}
            if a["type"] == "speak":
                c["scene"]["dialogue"] = {"speaker": pname, "speaker_id": "player", "portrait": ch.get("portrait"),
                                          "text": a["text"], "expression": "neutral", "style": "speech",
                                          "manner": a.get("manner"), "target": a.get("target"), "player": True}
    for a in take_story:
        store.push_event("action", {k: a.get(k) for k in ("id", "type", "manner", "target", "text", "display")})
    store.set_dm_status("thinking", last_action_at=_time.time(), idle_since=None)
    return take


def _public(a):
    return {k: a.get(k) for k in ("id", "type", "manner", "target", "text", "display", "created", "campaign", "data")
            if a.get(k) is not None}


@tool
def get_actions() -> dict:
    """Nudge mode / catch-up: return ALL pending browser actions (Speak/Do/DM) at once and mark them received.
    Resolve 'speak'/'do' in order as normal turns; answer 'dm' ones with dm_reply (no story effect)."""
    acts = _take()
    return {"actions": [_public(a) for a in acts], "mode": store.control()["mode"]}


MAX_WAIT = 50


def _idle_advice(idle):
    if idle >= 600:
        return None
    return MAX_WAIT  # the desktop bridge drops tool calls after ~60s, so never wait longer


def poll_once():
    """Shared by the sync (CLI) and async (MCP) await_action: returns a result dict or None to keep waiting."""
    ctl = store.control()
    if ctl.get("paused"):
        store.set_dm_status("idle", reason="paused")
        return {"action": None, "paused": True, "advice": "Player paused the DM. End your turn; resume when they chat."}
    got = _take(1)
    if got:
        return {"action": _public(got[0]), "mode": ctl["mode"]}
    return None


def await_start():
    d = store.dm_status()
    idle_since = d.get("idle_since") or _time.time()
    store.set_dm_status("listening", idle_since=idle_since)
    return idle_since


def await_timeout(idle_since):
    idle = _time.time() - idle_since
    nxt = _idle_advice(idle)
    if nxt is None:
        store.set_dm_status("idle", reason="timeout", idle_since=None)
        return {"action": None, "idle_s": int(idle), "stop": True,
                "advice": "Idle ~10 min: stop listening, end your turn with a one-line chat note ('say go to resume')."}
    store.set_dm_status("listening", idle_since=idle_since)
    return {"action": None, "idle_s": int(idle), "stop": False, "next_timeout_s": nxt,
            "advice": f"No input yet. Call await_action(timeout_s={nxt}) again."}


@tool
def await_action(timeout_s: int = 50) -> dict:
    """LIVE MODE: wait for the player's next browser action (Speak/Do/DM) and return it. Returns {action:{type,manner,
    target,text}} or, on timeout, {action:null, next_timeout_s} (call again with that value) or {stop:true} after ~10
    idle minutes (then end your turn). Returns immediately with paused:true if the player paused the DM."""
    idle_since = await_start()
    end = _time.time() + max(1, min(int(timeout_s), MAX_WAIT))
    while _time.time() < end:
        r = poll_once()
        if r:
            return r
        _time.sleep(0.4)
    return await_timeout(idle_since)


@tool
def dm_reply(text: str) -> dict:
    """Out-of-character answer to the player's DM-tab message. Shows in the browser DM panel only; no story effect,
    no turn, not voiced."""
    with _campaign() as c:
        c.setdefault("ooc", []).append({"from": "dm", "text": text, "t": now_iso()})
    store.push_event("dm_reply", {"text": text})
    return {"ok": True}


@tool
def set_input(enabled: bool = True, hint: str = "") -> dict:
    """Lock/unlock the browser action bar with an optional hint (e.g. 'Roll pending...', 'Pick a look in chat')."""
    store.set_dm_status(None, input={"enabled": enabled, "hint": hint})
    return {"ok": True}


# =====================================================================
# RECAP
# =====================================================================
@tool
def recap(previously: str = "", show: bool = False) -> dict:
    """Compact 'story so far' (about 1-2k tokens) for starting a NEW chat session - call right after load_campaign
    instead of reading raw logs. previously: store a player-facing 'Previously on...' paragraph (write one at the end
    of every session). show: display (and voice) the stored 'Previously on...' in the browser."""
    if previously:
        with _campaign() as c:
            c["previously"] = previously
            c.setdefault("dm", {}).setdefault("recaps", []).append({"turn": c["turn"], "text": previously})
    c = _load()
    ch = c["character"]; w = c["world"]
    brief = lambda a: {k: a.get(k) for k in ("name", "archetype", "level", "resources", "conditions", "attitude") if a.get(k) not in (None, [], {}, "")}
    turns = [l["text"] for l in c.get("log", []) if l.get("kind") == "turn"][-12:]
    lines = [(l.get("speaker") + ": " if l.get("speaker") else "") + l["text"]
             for l in c.get("log", []) if l.get("kind") in ("narration", "speech", "action")][-8:]
    dm = c.get("dm", {})
    out = {
        "campaign": {k: c.get(k) for k in ("id", "name", "theme", "status", "turn", "settings")},
        "run": len(c.get("runs", [])), "legacy": c.get("legacy", []),
        "previously": c.get("previously", ""),
        "character": {**brief(ch), "stats": ch.get("stats"), "currency": ch.get("currency"), "xp": ch.get("xp"),
                      "pronouns": ch.get("pronouns"), "abilities": ch.get("abilities"),
                      "inventory": [f"{i.get('name')} x{i.get('qty', 1)}" + (" (eq)" if i.get("equipped") else "")
                                    for i in ch.get("inventory", [])], "hooks": ch.get("hooks")},
        "party": [brief(p) for p in c.get("party", [])],
        "where": {"location": w.get("location"), "map": w.get("map"), "pos": w.get("pos"), "time": w.get("time"),
                  "weather": w.get("weather"), "mode": c["scene"].get("mode"),
                  "on_stage": [f"{e.get('name')} ({e.get('side')})" for e in c["scene"].get("entities", [])]},
        "combat": c.get("combat") if c.get("combat", {}).get("active") else None,
        "quests": [{"title": q["title"], "status": q["status"],
                    "open": [o["text"] for o in q.get("objectives", []) if not o.get("done")]}
                   for q in c.get("quests", []) if q.get("status") in ("active", "hidden")],
        "recent_turns": turns, "last_lines": lines,
        "npcs": w.get("npcs", {}), "flags": w.get("flags", {}),
        "dm": {"scenario": dm.get("scenario"), "secrets": dm.get("secrets", [])[-5:],
               "plans": dm.get("plans", [])[-5:], "notes": dm.get("notes", [])[-5:]},
    }
    if show and out["previously"]:
        theme = assets.load_theme(c["theme"]) or {}
        v = tts.norm_voice((theme.get("voices") or {}).get("narrator")) or tts.DEFAULT_NARRATOR
        store.push_event("previously", {"text": out["previously"], "voice": v})
    return out


# =====================================================================
# RESET
# =====================================================================
@tool
def reset_game(clear_pending: bool = True) -> dict:
    """Return the browser to the MAIN MENU (Save & Quit). Deactivates the current campaign
    (its file is kept untouched and can be reloaded with load_campaign), stops listening and, by default, discards any
    queued browser actions. Nothing is deleted. Use when the player asks to reset/quit to title."""
    prev = store.runtime().get("active")
    dropped = 0
    if clear_pending:
        with store.file_lock("inbox"):
            ib = store.inbox()
            for a in ib["actions"]:
                if a.get("status") == "pending":
                    a["status"] = "cancelled"; dropped += 1
            store.write_json(store.INBOX, ib)
    store.set_dm_status("idle", reason="reset", idle_since=None, input={"enabled": True, "hint": ""}, loading=None)
    store.set_active(None)
    return {"ok": True, "deactivated": prev, "pending_discarded": dropped,
            "note": "Campaign files are kept; list_campaigns / load_campaign to resume."}



# =====================================================================
# MENU REQUEST HELPERS
# =====================================================================
@tool
def loading(label: str = "", percent: int | None = None, done: bool = False) -> dict:
    """Show/update the browser loading bar while you work on something slow (building a theme, preparing a new game,
    resuming). percent 0-100 or omit for an indeterminate bar. done=True hides it."""
    store.set_loading(label, percent, done)
    return {"ok": True}


@tool
def theme_ready(theme: str, note: str = "") -> dict:
    """Tell the New Game wizard that the theme it requested (build_theme) is built/modified and selected, so the player
    can continue to the next wizard page. Hides the loading bar."""
    if not assets.load_theme(theme):
        raise DMError(f"theme '{theme}' not found")
    store.update_draft({"theme": theme, "theme_status": "ready", "theme_note": note, "page": max(2, store.draft().get("page", 1))})
    store.set_loading(done=True)
    store.push_event("wizard", {"theme": theme})
    return {"ok": True}


@tool
def theme_failed(reason: str) -> dict:
    """Tell the wizard a theme build request could not be completed (shows the reason to the player)."""
    store.update_draft({"theme_status": "failed", "theme_note": reason})
    store.set_loading(done=True)
    store.push_event("wizard", {"failed": reason})
    return {"ok": True}



def campaign_from_wizard(d: dict) -> str:
    """Create a campaign from the browser New Game wizard draft (server-side, no DM needed). Returns campaign id."""
    theme = d.get("theme")
    if not theme or not assets.load_theme(theme):
        raise DMError("pick or build a theme first")
    ch = d.get("character") or {}
    if not ch.get("name"):
        raise DMError("your character needs a name")
    rules = d.get("rules") or {}
    name = (d.get("campaign_name") or "").strip() or f"The Tale of {ch['name']}"
    r = new_campaign(name, theme, {k: rules.get(k) for k in ("tone", "content_limits", "limits_note", "difficulty",
                                                                   "permadeath", "session_length") if rules.get(k) is not None},
                     {"source": "browser wizard"})
    ch["hooks"] = [h.strip() for h in (ch.get("hooks") or []) if h and str(h).strip()]
    fields = {k: ch.get(k) for k in ("name", "pronouns", "archetype", "stats", "sprite", "portrait", "backstory", "hooks")
              if ch.get(k) not in (None, "", [], {})}
    if ch.get("look"):
        fields["look"] = ch["look"]
    set_character(fields)
    dm_notes(set={"setup": {"archetype_id": ch.get("archetype_id"), "stats_method": ch.get("stats_method"),
                            "party": d.get("party") or {"mode": "solo"}}})
    return r["campaign_id"]
