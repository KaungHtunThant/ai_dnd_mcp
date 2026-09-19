"""Register (or remove) the Claude DnD MCP server in the Claude desktop app config.
Backs up the existing config first.   python register_mcp.py [--remove]"""
import json, os, sys, shutil, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NAME = "claude-dnd"


def candidates():
    out = []
    appdata = os.environ.get("APPDATA")
    local = os.environ.get("LOCALAPPDATA")
    if appdata:
        out.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
    if local:  # Microsoft Store (MSIX) install keeps a virtualised copy
        pk = Path(local) / "Packages"
        if pk.exists():
            for d in pk.glob("Claude_*"):
                out.append(d / "LocalCache" / "Roaming" / "Claude" / "claude_desktop_config.json")
    home = Path.home()
    out.append(home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")  # macOS
    out.append(home / ".config" / "Claude" / "claude_desktop_config.json")  # linux
    return out


def main():
    remove = "--remove" in sys.argv
    py = Path(sys.executable)
    if os.name == "nt":
        venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = ROOT / ".venv" / "bin" / "python"
    py = venv_py if venv_py.exists() else py
    entry = {"command": str(py), "args": [str(HERE / "mcp_server.py")], "env": {"CLAUDE_DND_ROOT": str(ROOT)}}
    targets = [p for p in candidates() if p.parent.exists()]
    if not targets:
        p = candidates()[0]; p.parent.mkdir(parents=True, exist_ok=True); targets = [p]
    for cfgp in targets:
        cfg = {}
        if cfgp.exists():
            try:
                cfg = json.loads(cfgp.read_text(encoding="utf-8") or "{}")
            except json.JSONDecodeError:
                print(f"!! {cfgp} is not valid JSON - not touching it. Add the entry manually:")
                print(json.dumps({NAME: entry}, indent=2)); continue
            bak = cfgp.with_name(f"claude_desktop_config.backup-{datetime.datetime.now():%Y%m%d-%H%M%S}.json")
            shutil.copy2(cfgp, bak); print(f"Backup: {bak}")
        servers = cfg.setdefault("mcpServers", {})
        if remove:
            servers.pop(NAME, None); print(f"Removed '{NAME}' from {cfgp}")
        else:
            servers[NAME] = entry; print(f"Registered '{NAME}' in {cfgp}")
        cfgp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(json.dumps({NAME: entry}, indent=2))


if __name__ == "__main__":
    main()
