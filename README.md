# Claude DnD

A roguelike, tabletop-style visual novel. **Claude is the Dungeon Master** in the chat, and this folder holds the
game's engine, art library, themes and campaign saves. The local UI (a browser page) only shows scenes, characters, maps,
stats and dice. You play by typing what you do in the chat.

## First-time setup (Windows)
1. Double-click **`setup.bat`**. It:
   - creates a private virtual environment in `.venv` (nothing is installed system-wide),
   - installs the only dependency (`mcp`) into it,
   - registers the `claude-dnd` MCP server in the Claude desktop app config (a backup of your config is saved first).
2. **Fully quit and reopen the Claude desktop app.**
3. In chat, say **"go"** (once per play session) so the DM connects. The game opens at http://127.0.0.1:8765/ with the
   main menu: **New Game** (a setup wizard for world, rules, character, stats, look and party), **Continue** (your saves) and
   **Settings**.

Requires Python 3.10+. To undo: `uninstall_mcp.bat`, then delete `.venv`.
If you only want the screen without the MCP (the DM then uses the command-line fallback), run `start_ui.bat`.

## Folder layout
```
Claude DnD/
  engine/        MCP server, UI server, web front end, pixel-art generator, DM guide
  shared/        shared template library (≈210 mix-and-match parts) + catalog.html to browse them
  themes/<name>/ one reusable library per theme: theme.json, manifest.json, assets/, maps/, npcs/, lore/, tables/
  campaigns/     one JSON file per campaign (all campaign + player data, snapshots, hidden DM notes = spoilers!)
  config.json    UI host/port, browser auto-open, rollback depth
```

## How the art works
Everything is pixel art built from layers (body, clothes, hair, hats, gear; portrait base, face expression, outfit...)
and recoloured through named colour slots. A theme reuses the shared templates and only saves new parts when the
story needs something that doesn't exist yet. Every new part is stored in the theme and reused next time.
Open `shared/catalog.html` to see the library.

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
