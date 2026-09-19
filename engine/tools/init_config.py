"""Create config.json for this machine and ask which port the browser UI should use.

Run by setup.bat. config.json is gitignored (it is per-machine, like a .env);
config.sample.json is the committed template.

    python engine/tools/init_config.py            # interactive
    python engine/tools/init_config.py --port 8770 --yes
    python engine/tools/init_config.py --yes      # accept current/default, no prompt
"""
import os, socket, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core import store

LOW, HIGH = 1024, 65535


def in_use(host, port) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, int(port))) == 0


def free_port(host, start) -> int:
    for p in range(int(start), min(int(start) + 40, HIGH)):
        if not in_use(host, p):
            return p
    return int(start)


def ask_port(host, current) -> int:
    """Prompt until the answer is a usable port. Empty input keeps `current`."""
    while True:
        busy = in_use(host, current)
        hint = f" (something is already listening on {current})" if busy else ""
        suggested = free_port(host, current + 1) if busy else current
        try:
            raw = input(f"Browser UI port [{suggested}]{hint}: ").strip()
        except EOFError:
            return suggested
        if not raw:
            return suggested
        if not raw.isdigit() or not (LOW <= int(raw) <= HIGH):
            print(f"  Enter a number between {LOW} and {HIGH}.")
            continue
        port = int(raw)
        if in_use(host, port):
            print(f"  Port {port} is already in use on {host}. Pick another, or stop whatever is using it.")
            continue
        return port


def main(argv):
    port = None
    assume_yes = "--yes" in argv or "-y" in argv
    if "--port" in argv:
        i = argv.index("--port")
        if i + 1 < len(argv) and argv[i + 1].isdigit():
            port = int(argv[i + 1])

    existing = store.CONFIG.exists()
    cfg = store.ensure_config()          # writes it from config.sample.json on first run
    host = cfg.get("ui_host", "127.0.0.1")

    if port is None:
        if assume_yes:
            port = cfg["ui_port"]
        else:
            print(f"\nSettings file: {store.CONFIG}")
            print("  (this one is yours - it is not committed; config.sample.json is the shared template)")
            if existing:
                print(f"  Keeping your existing settings. Press Enter to stay on port {cfg['ui_port']}.")
            port = ask_port(host, int(cfg["ui_port"]))

    if not (LOW <= int(port) <= HIGH):
        print(f"Port must be between {LOW} and {HIGH}.")
        return 1

    cfg["ui_port"] = int(port)
    store.write_json(store.CONFIG, cfg)
    print(f"\nUI will run at http://{host}:{cfg['ui_port']}/")
    if in_use(host, cfg["ui_port"]):
        print("  Note: that port is in use right now - if it is an old copy of this app, close it first.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
