"""CLI fallback - same tools as the MCP server.
  python dm.py <tool> '<json args>'      e.g.  python dm.py narrate '{"text":"The door creaks."}'
  python dm.py tools                     list tools
  python dm.py help <tool>               show a tool's docs
"""
import os, sys, json, inspect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import api, store  # noqa: E402

if __name__ == "__main__":
    store.ensure_dirs()
    if len(sys.argv) < 2 or sys.argv[1] == "tools":
        print("\n".join(sorted(api.TOOLS))); sys.exit(0)
    if sys.argv[1] == "help":
        fn = api.TOOLS[sys.argv[2]]; print(sys.argv[2] + str(inspect.signature(fn))); print(inspect.getdoc(fn)); sys.exit(0)
    fn = api.TOOLS.get(sys.argv[1])
    if not fn:
        print(json.dumps({"error": f"unknown tool {sys.argv[1]}"})); sys.exit(1)
    raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
    if raw == "-":
        raw = sys.stdin.read()
    args = json.loads(raw) if raw.strip() else {}
    try:
        print(json.dumps(fn(**args), ensure_ascii=False, indent=1))
    except api.DMError as e:
        print(json.dumps({"error": str(e)})); sys.exit(2)
