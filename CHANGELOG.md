# Changelog

All notable changes to Claude DnD. Newest first.

## Unreleased

### Art styles, chosen before anything is generated

The New Game wizard now asks for an art style on its first page, next to the theme.
A style is not a second set of artwork: it transforms the final colour of every pixel
and changes how outlines and automatic shading behave, so one choice restyles every
sprite, portrait, tile, item and backdrop at once.

**Added**
- `engine/core/style.py` with eight styles — Classic, Flat, Neon, Noir, Pastel,
  Ink Wash, Sepia, Game Boy. Each sets `saturation`, `lightness`, `contrast` (the depth
  of the `:d` / `:l` shading, 0 = flat), an `outline` mode (`dark` / `none` / `light` /
  a hex) and an optional `ramp` that quantises every colour to one palette by luminance,
  which is what makes Sepia and Game Boy read as a single ink.
- Art style picker on wizard page 1, with a live-rendered portrait and sprite per style.
- `list_styles()` and `set_style(style, scope="campaign"|"theme")` tools. `theme_info`
  reports the resolved style.
- `theme.json["style"]` is the theme default; a campaign may override it. Resolution is
  campaign -> theme -> classic, cached on file mtimes so a render is not a file read.
- `?st=` on `/r/`, `/part/` and `/map/`, used by the picker to preview and part of the
  render cache key.

**Changed**
- `pixel.color_of` / `grid_rects` / `render_grid`, `assets.render_recipe` /
  `render_map` take a style; `create_theme(style=...)` sets it at build time.
- The wizard's choice rides along with `build_theme`, so a theme the DM builds is born
  in the chosen style, and `campaign_from_wizard` applies it to the campaign.
- Image URLs in the front end carry the active style, so changing it busts the browser
  cache instead of showing stale art.
- A theme's catalog renders in, and names, its style.

### Theme-locked art library

The ~210 procedural parts (`tpl:*`) used to be a single global library that every
theme could reach into, so a cyberpunk campaign was one `find_assets` call away from
a wizard hat. Each theme now declares its own vocabulary and anything outside it is
refused.

**Added**
- `engine/core/library.py` — the single authority on what a theme may draw with.
  `allowed()` / `admits()` / `check()` / `check_recipe()` / `templates_for()` /
  `summary()` / `split_pairs()`. The resolved set is cached on `theme.json`'s mtime,
  so `update_theme` invalidates it for free.
- `theme.json` → `library`: `{"mode":"locked"|"open", "core":bool, "include_tags":[],
  "include":[], "exclude":[]}`. Resolution is `core ∪ tag matches ∪ include − exclude`;
  `include`/`exclude` take template names or globs and `exclude` is applied last.
- `core: true` admits 78 genre-neutral parts (every UI icon, the 11 face expressions,
  bodies, legs, boots, hair, `tile_void`) so a theme does not have to enumerate
  scaffolding. `exclude` can still strip any of it.
- `create_theme(library_=...)` sets the vocabulary at build time; `theme_info` reports it.
- `library.split_pairs()` flags sprite/portrait counterparts where only one half is
  admitted (e.g. `eyepatch` without `p_eyepatch`) — a character silently losing a
  feature on their portrait. Surfaced in `theme_info` and on the catalog page.
- `GET /catalog` (and `/catalog/<theme>`) serves the active theme's catalog, rebuilding
  it when stale.
- `store.DMError` as a shared base, so `library.NotInTheme` reports as a clean message
  instead of a traceback.

**Changed**
- The lock is hard and fires at two depths: `assets.resolve_part` raises `NotInTheme`
  for a known template outside the vocabulary, and every tool that *stores* a recipe
  validates up front — `set_scene`, `spawn`, `set_character`, `update_entity`,
  `add_companion`, `create_npc`, `create_map` (backdrop, each legend tile, each object)
  and `create_asset`. Without the second layer a bad part was accepted and then quietly
  failed to draw. An *unknown* ref still returns `None`, which keeps the
  `{expr}` → `neutral` portrait fallback working.
- `find_assets` only lists what the theme admits.
- The catalog is per theme: `themes/<slug>/catalog.html` + `TEMPLATES.md`, admitted parts
  only, drawn in the theme's own palette, with the theme's archetypes as the sample mixes
  (replacing hardcoded knight/mage/netrunner samples). `build_catalog.py` takes a slug, or
  builds every theme with no arguments. Regenerate rebuilds them all.
- `ui_server` SVG rendering degrades to an empty image rather than a 500 when a recipe
  saved before the vocabulary narrowed can no longer be drawn.

**Removed**
- `shared/catalog.html`, `engine/TEMPLATES.md`, the `shared/` folder and `store.SHARED`.
  To eyeball a brand-new template, view it in any theme whose `library.mode` is `"open"`.

**Migration** — a theme with no `library` block is `"open"` and behaves exactly as before.

### config.json is local, like a .env

**Added**
- `config.sample.json`, the committed template.
- `engine/tools/init_config.py` — creates `config.json` and asks which port the browser UI
  should use. Probes the port, suggests the next free one when the default is taken,
  rejects non-numeric input and anything outside 1024–65535, and re-asks on a busy port.
  `--port N --yes` for non-interactive use. Run by `setup.bat`; `start_ui.bat` runs it too
  when the file is missing.
- `store.CONFIG_DEFAULTS` and `store.ensure_config()`, called from `ensure_dirs()`, so a
  fresh clone with no `config.json` boots and writes one from the sample.

**Changed**
- `config.json` is gitignored and removed from the index — it is per-machine state.
- `store.config()` fills in any missing key from `CONFIG_DEFAULTS`, so a partial or absent
  file never stops the engine.
- Docs no longer hardcode port 8765; the DM takes the url from `init()`.
