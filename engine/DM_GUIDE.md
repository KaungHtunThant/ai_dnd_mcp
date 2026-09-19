# Claude DnD - DM guide (for Claude)

The MCP server `claude-dnd` only **displays and stores** the game. Story, choices and conversation happen in chat.
The player types actions in chat; I narrate in chat and mirror the key beats on screen.

## Golden rules
1. **Reuse before create.** Themes are libraries shared by every campaign in that theme.
   Before making anything: `find_assets`, `find_maps`, `find_npcs`, `find_lore`, `table("list")`.
   Shared templates (`tpl:*`, ~210 parts) are always available and need no files. Only `create_asset` /
   `create_map` / `create_npc` / `write_lore` when nothing fits - and make new things generic enough to reuse.
2. **Theme = reusable truth, campaign = what happened.** Map layouts, NPC looks and personalities, and world facts go in the
   theme. Who died, which doors opened, attitudes and flags go in the campaign (`npc_state`, `dm_notes`, `marker`,
   quests, journal).
3. **Secrets live in `dm_notes`** (the scenario, twists, hidden DCs, plans). Never put spoilers in narrate/journal.
4. **Dice are real.** Use `roll` for every uncertain outcome. Let the result stand. Hidden rolls use hidden=true.
5. **Each resolved player action -> `end_turn(summary)`.** This saves a rollback snapshot.
6. **Roguelike:** death is real when permadeath is on. `end_run(cause, legacy)` then run character creation again
   within the same campaign, applying the legacy perks.

## Session flow
- Player says "init" / "new campaign" -> `init()` -> ask the steps **one at a time** in chat:
  theme -> tone/limits/difficulty -> character (name, pronouns, archetype, stats, look, hooks) -> party.
- New theme: `create_theme(...)` with fitting stats/resources/terms/ui. Existing theme: reuse it as it is.
- `new_campaign(name, theme, settings, player)` -> the setup screen appears.
- Character look: `showcase()` a few numbered options (sprites or portraits), then `set_character` updates live.
- Write the secret scenario: `dm_notes(set={"scenario":{premise, acts:[...], antagonist, twist, ending_conditions}})`.
- `finish_setup()` -> opening: `set_scene` + `spawn` + `narrate`/`say`.
- Resume later: `list_campaigns` -> `load_campaign(id)` -> `get_state()` -> recap.

## Browser input, voice, recap (details in CLAUDE.md)
- Live mode: `await_action(timeout_s)` → resolve → `end_turn` → `await_action` again (follow `next_timeout_s`; stop on
  `stop`/`paused`). Nudge mode: `get_actions()` when the player says "go".
- speak = in-character line (manner + optional target), do = action, dm = out-of-character → `dm_reply` only.
- Voices: `list_voices`, `set_voice`; narrator + NPC templates are stored in the theme.
- New session: `load_campaign` → `recap(show=True)`. End of session: `recap(previously="...")`.

## Every turn
1. Read the player's action. 2. If uncertain, `roll` (with dc). 3. Apply consequences (`update_stats`,
`condition`, `inventory`, `quest`, `move_player`, `reveal`, `update_entity`). 4. Show it (`narrate` 1-4 sentences,
`say` for dialogue with an expression, `effect` for impact). 5. Write the fuller prose in chat and end with
what the player sees and a prompt (no forced menu unless helpful). 6. `end_turn(summary)`.

## Recipes (how looks are built)
```json
{"layers": ["tpl:cloak","tpl:body","tpl:legs_pants","tpl:boots","tpl:top_coat","tpl:hair_long","tpl:hat_wide","tpl:held_gun"],
 "colors": {"skin":"#c98e62","hair":"#2a1a10","top":"#6b4a2e","accent":"#3a2d25"},
 "params": {"build":"normal"}}
```
- Layers are auto-sorted by z (back < body < legs < boots < top < face < beard < hair < hat < held).
- A layer may be an object: `{"part":"tpl:cr_beast","params":{"horns":true},"colors":{"primary":"#553"},"dx":0,"dy":0}`.
- Portraits: `["tpl:p_hair_back"?, "tpl:p_base", "tpl:p_face_{expr}", "tpl:p_outfit_*", "tpl:p_hair_*", "tpl:p_hat_*", extras]`.
  `{expr}` becomes the expression passed to `say` (neutral happy laugh angry sad surprised smirk hurt calm determined scared).
- Sprite 16x24: body, hair_*, beard, top_* (shirt coat robe armor jacket vest), legs_pants/skirt, boots, hat_* (hood helmet cap
  wizard wide), crown, horns, ears_pointy, mask, goggles, eyepatch, cloak, wings, tail, held_* (sword staff dagger gun rifle bow
  axe torch), offhand_* (shield lantern book).
- Creatures: cr_slime bat beast spider skeleton ghost golem serpent eye drone plant rat drake (colour with primary/secondary/glow/eyes).
- Colour slots: skin hair top accent legs boots metal wood glow eyes white mouth primary secondary detail outline
  (each gets auto dark/light shades).
- Backdrops (scene mode): bd_outdoor(trees=pine|round|none) bd_interior bd_city bd_cave bd_void bd_ruins bd_tech.
- Themes are **locked to a vocabulary**: `find_assets` only lists what the theme admits, and referencing a real
  template outside it raises `NotInTheme`. The lists above are the whole engine library, not necessarily this theme's.
- Full list for the active theme: `themes/<slug>/TEMPLATES.md` / visual: `/catalog` in the browser
  (`themes/<slug>/catalog.html`), drawn in the theme's palette.

## Maps
Small (≈12-24 × 8-16). `create_map(rows, legend)`, legend char -> `{"tile":"tpl:tile_*","solid":bool,"name":..,"colors":{..},"under":"."}`.
Tiles: floor_stone/wood/metal/tile, grass, dirt, sand, snow, water, lava, void, road, rubble, wall_brick/rock/metal/wood/hedge,
door, door_open, stairs_down/up, bridge, tree, rock, pillar. Static decor via `objects`. `load_map` -> `move_player` (auto-reveal) ->
`spawn(x,y)` for creatures/NPCs on tiles -> `marker` for points of interest.

## Theme design checklist (new themes only)
stats (6, themed names), resources (hp + one themed: sanity/heat/ammo/mana...), currency, 3-5 archetypes, conditions,
ui colours + font (pixel|serif|mono|sans), terms (rename Items/Quests/Journal/Log/Party). Palette sets default slot colours.
