"""Paths + robust JSON file IO shared by MCP server, CLI and UI server."""
from __future__ import annotations
import json, os, re, threading, time, datetime, contextlib, secrets
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_DND_ROOT") or Path(__file__).resolve().parents[2])
ENGINE = ROOT / "engine"
THEMES = ROOT / "themes"
CAMPAIGNS = ROOT / "campaigns"
RUNTIME = ROOT / "runtime.json"
CONFIG = ROOT / "config.json"
CONFIG_SAMPLE = ROOT / "config.sample.json"
INBOX = ROOT / "inbox.json"          # browser -> DM action queue (transient)
CONTROL = ROOT / "control.json"      # browser-set play controls (mode, paused)
DMSTATUS = ROOT / "dm_status.json"   # DM-set status (listening / thinking / idle, input lock)
CACHE = ROOT / "cache"
DRAFT = ROOT / "setup_draft.json"    # New Game wizard draft (browser)
_lock = threading.RLock()


class DMError(Exception):
    """Any error worth showing the DM as a plain message instead of a traceback."""


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(s).strip().lower()).strip("-")
    return s or "untitled"


def read_json(path, default=None):
    path = Path(path)
    for _ in range(20):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return default
        except (json.JSONDecodeError, PermissionError, OSError):
            time.sleep(0.03)
    return default


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        for i in range(50):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:  # Windows: reader has it open
                time.sleep(0.02 * (i + 1))
        raise


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


CONFIG_DEFAULTS = {"ui_host": "127.0.0.1", "ui_port": 8765, "open_browser": True, "snapshots_kept": 20}


def config():
    """Local settings. config.json is per-machine and gitignored; config.sample.json is the
    committed template. Missing keys fall back to CONFIG_DEFAULTS, so a missing or partial
    file never stops the engine."""
    cfg = read_json(CONFIG, {}) or {}
    for k, v in CONFIG_DEFAULTS.items():
        cfg.setdefault(k, v)
    return cfg


def ensure_config():
    """Materialise config.json from config.sample.json (or the built-in defaults) on first run,
    so every install has a real file to edit. Returns the config."""
    if not CONFIG.exists():
        base = read_json(CONFIG_SAMPLE, None) or dict(CONFIG_DEFAULTS)
        write_json(CONFIG, {**CONFIG_DEFAULTS, **base})
    return config()


# ---- runtime: active campaign + UI event stream ---------------------------
def runtime():
    rt = read_json(RUNTIME, None) or {}
    rt.setdefault("active", None)
    rt.setdefault("seq", 0)
    rt.setdefault("events", [])
    return rt


def set_active(campaign_id):
    with _lock:
        rt = runtime(); rt["active"] = campaign_id; rt["seq"] += 1
        rt["events"].append({"seq": rt["seq"], "type": "reload", "data": {}, "t": now_iso()})
        rt["events"] = rt["events"][-200:]
        write_json(RUNTIME, rt)


def push_event(etype, data=None):
    with _lock:
        rt = runtime(); rt["seq"] += 1
        ev = {"seq": rt["seq"], "type": etype, "data": data or {}, "t": now_iso()}
        rt["events"].append(ev); rt["events"] = rt["events"][-200:]
        write_json(RUNTIME, rt)
        return ev


def touch():
    """Bump seq so the UI refreshes state without a visual event."""
    return push_event("state")


def ensure_dirs():
    for d in (THEMES, CAMPAIGNS):
        d.mkdir(parents=True, exist_ok=True)
    ensure_config()


# ---- cross-process lock (UI server and MCP both touch inbox.json) ----------
@contextlib.contextmanager
def file_lock(name="inbox", timeout=5.0):
    p = ROOT / f".{name}.lock"
    t0 = time.time(); got = False
    while True:
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd); got = True; break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(p) > 10:
                    os.remove(p); continue
            except OSError:
                pass
            if time.time() - t0 > timeout:
                break
            time.sleep(0.02)
        except OSError:
            break
    try:
        yield
    finally:
        if got:
            with contextlib.suppress(OSError):
                os.remove(p)


def inbox():
    ib = read_json(INBOX, None) or {}
    ib.setdefault("actions", []); ib.setdefault("next_id", 1)
    return ib


def control():
    c = read_json(CONTROL, None) or {}
    c.setdefault("mode", "live"); c.setdefault("paused", False)
    return c


def dm_status():
    d = read_json(DMSTATUS, None) or {}
    d.setdefault("status", "idle"); d.setdefault("t", 0); d.setdefault("input", {"enabled": True, "hint": ""})
    return d


def set_dm_status(status=None, **extra):
    with _lock:
        d = dm_status()
        if status:
            d["status"] = status
        d.update(extra); d["t"] = time.time()
        write_json(DMSTATUS, d)
        return d


_TOKEN = secrets.token_hex(16)


def ui_token():
    return _TOKEN


def draft():
    return read_json(DRAFT, None) or {}


def update_draft(changes):
    with file_lock("draft"):
        d = draft(); d.update(changes); write_json(DRAFT, d)
        return d


def set_loading(label=None, percent=None, done=False):
    """DM/server-driven loading bar in the browser. done=True hides it."""
    return set_dm_status(None, loading=None if done else {"label": label or "Loading...", "percent": percent, "t": time.time()})
