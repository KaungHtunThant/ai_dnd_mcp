# Claude DnD

A roguelike, tabletop-style visual novel. **Claude is the Dungeon Master** in the chat, and this folder holds the
game's engine, art library, themes and campaign saves. The local UI (a browser page) only shows scenes, characters, maps,
stats and dice. You play by typing what you do in the chat.

## First-time setup (Windows)
1. Double-click **`setup.bat`**. It:
   - creates a private virtual environment in `.venv` (nothing is installed system-wide),
   - installs the only dependency (`mcp`) into it,
   - creates your `config.json` from `config.sample.json` and **asks which port** the browser UI should use
     (press Enter to take the suggested one; it skips ports already in use),
   - registers the `claude-dnd` MCP server in the Claude desktop app config (a backup of your config is saved first).
2. **Fully quit and reopen the Claude desktop app.**
3. In chat, say **"go"** (once per play session) so the DM connects. The game opens at the port you chose (8765 by
   default) with the
   main menu: **New Game** (a setup wizard for world, rules, character, stats, look and party), **Continue** (your saves) and
   **Settings**.

Requires Python 3.10+. To undo: `uninstall_mcp.bat`, then delete `.venv`.
If you only want the screen without the MCP (the DM then uses the command-line fallback), run `start_ui.bat`.

## Folder layout
```
Claude DnD/
  engine/        MCP server, UI server, web front end, pixel-art generator, DM guide
  themes/<name>/ one reusable library per theme: theme.json, manifest.json, assets/, maps/, npcs/, lore/, tables/,
                 plus a generated catalog.html of every part that theme is allowed to use
  campaigns/     one JSON file per campaign (all campaign + player data, snapshots, hidden DM notes = spoilers!)
  config.json    YOUR local settings - UI host/port, browser auto-open, rollback depth. Generated on setup and
                 never committed, like a .env; edit it freely or rerun `engine/tools/init_config.py`.
  config.sample.json  the committed template config.json is created from
```

## Art styles
Before anything is generated, the New Game wizard asks for an **art style**: *Classic, Flat, Neon, Noir, Pastel,
Ink Wash, Sepia* or *Game Boy*. It is not a second set of artwork — it transforms the final colour of every pixel,
plus outlines and shading depth, so one click restyles every sprite, portrait, tile, item and backdrop in the game.
The picker previews each one live. A style is saved on the theme and can be overridden for a single campaign.

## How the art works
Everything is pixel art built from layers (body, clothes, hair, hats, gear; portrait base, face expression, outfit...)
and recoloured through named colour slots. The engine ships ≈210 procedural parts, but each theme is **locked to its
own vocabulary**: it declares which parts fit its genre, and anything outside that set is refused, so a cyberpunk
campaign can never reach for a wizard hat. A theme reuses its admitted parts and only saves new ones when the story
needs something that doesn't exist yet. Every new part is stored in the theme and reused next time.
Open **`/catalog`** on the UI (the port from your `config.json`) while playing, to browse exactly what the current
theme can use, drawn in its own palette.

## Playing in the browser
- **Action bar** (under the dialogue box):
  - **Speak** — choose a manner (normal by default) and an optional *To:* name.
  - **Do** — describe any action.
  - **DM** — ask the DM out-of-character questions. These have no effect on the story, and answers appear in the DM tab.
  - Keys: Enter sends, Shift+Enter starts a new line, Alt+1/2/3 switches tabs. You can cancel a waiting action to edit it.
- **Top bar controls:**
  - **Live / Nudge** — Live: the DM waits for your browser input. Nudge: queue your actions, then type *go* in chat.
    Nudge uses no usage while idle.
  - **Pause DM** — stops the DM from waiting.
  - **Voice on/off** and a volume slider — narrator and characters are voiced with neural voices (needs internet).
    Your own lines are never voiced.
- Click the dialogue box (or press Space) to skip typing and move to the next page. The side tabs show Items, Quests,
  Journal, Story and DM.

After updating the engine, run `setup.bat` again to install new packages (it reuses `.venv`), then restart the
Claude desktop app.
