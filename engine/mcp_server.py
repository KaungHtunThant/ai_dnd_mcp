"""Claude DnD MCP server (stdio). Registers every tool in core/api.py and runs the UI server in a thread."""
from __future__ import annotations
import os, sys, json, functools, inspect, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP  # noqa: E402
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP  # noqa: E402
from core import api, store  # noqa: E402
import ui_server  # noqa: E402

INSTRUCTIONS = """Claude DnD - you are the Dungeon Master. This server only drives the visual novel UI and stores
state; the story and player interaction happen in chat. Start with `init`. Reuse the theme library first
(find_assets, find_maps, find_npcs, find_lore) and only create_* what is missing. Read engine/DM_GUIDE.md for recipes,
legend and conventions."""

mcp = FastMCP("claude-dnd", instructions=INSTRUCTIONS)


def _ensure_ui():
    url = ui_server.start_in_thread()
    cfg = store.config()
    flag = store.ROOT / ".browser_opened"
    if cfg.get("open_browser") and not flag.exists():
        try:
            import webbrowser; webbrowser.open(url)
            flag.write_text("1")
        except Exception:
            pass
    return url


api.UI_HOOK["ensure_ui"] = _ensure_ui


def _wrap(fn):
    @functools.wraps(fn)
    def w(*a, **k):
        try:
            return fn(*a, **k)
        except api.DMError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-800:]}
    w.__signature__ = inspect.signature(fn)
    return w


async def await_action(timeout_s: int = 50) -> dict:
    import asyncio, time
    try:
        idle_since = api.await_start()
        end = time.time() + max(1, min(int(timeout_s), 600))
        while time.time() < end:
            r = api.poll_once()
            if r:
                return r
            await asyncio.sleep(0.4)
        return api.await_timeout(idle_since)
    except api.DMError as e:
        return {"error": str(e)}


for name, fn in api.TOOLS.items():
    if name == "await_action":  # non-blocking async version for the MCP event loop
        mcp.tool(name=name, description=inspect.getdoc(fn))(await_action)
        continue
    mcp.tool(name=name, description=inspect.getdoc(fn))(_wrap(fn))


if __name__ == "__main__":
    store.ensure_dirs()
    try:
        ui_server.start_in_thread()
    except Exception:
        pass
    mcp.run()
