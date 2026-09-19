"""Local visual UI server (stdlib only). Read-only view of the active campaign.

  python ui_server.py            -> serves http://127.0.0.1:8765/
Endpoints: / (app), /web/*, /api/state, /api/events?since=N, /api/stream (SSE),
           /r/<theme>.svg?r=<recipe json>&e=<expr>, /map/<theme>/<id>.svg, /part/<theme>/<ref>.svg
"""
from __future__ import annotations
import json, os, sys, threading, time, functools, mimetypes, socket, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import store, assets, api, tts, dice  # noqa: E402

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def _mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0


@functools.lru_cache(maxsize=4096)
def _render(theme, recipe_json, expr, ver):
    t = assets.load_theme(theme) if theme and theme != "_" else None
    return assets.render_recipe(theme if t else None, json.loads(recipe_json), (t or {}).get("palette"), expr or None)


@functools.lru_cache(maxsize=64)
def _render_map(theme, mid, ver):
    t = assets.load_theme(theme) or {}
    m = assets.load_map(theme, mid)
    return assets.render_map(theme, m, t.get("palette")) if m else None


def _ver(theme):
    if not theme or theme == "_":
        return 0
    d = assets.theme_dir(theme)
    return _mtime(d / "manifest.json") + _mtime(d / "theme.json")


def _campaign_card(p):
    c = store.read_json(p, None)
    if not c or not c.get("id"):
        return None
    t = assets.load_theme(c.get("theme")) or {}
    ch = c.get("character") or {}
    runs = c.get("runs", [])
    return {"id": c["id"], "name": c.get("name"), "theme": c.get("theme"), "theme_name": t.get("name", c.get("theme")),
            "status": c.get("status"), "turn": c.get("turn", 0), "updated": c.get("updated"),
            "location": (c.get("world") or {}).get("location"),
            "character": {"name": ch.get("name"), "archetype": ch.get("archetype"), "level": ch.get("level"),
                          "portrait": ch.get("portrait")},
            "runs": len(runs), "deaths": sum(1 for r in runs if r.get("ended") and r.get("cause") not in ("complete", "abandoned")),
            "backdrop": (c.get("scene") or {}).get("backdrop")}


def menu_payload():
    saves = [x for x in (_campaign_card(p) for p in store.CAMPAIGNS.glob("*.json")) if x]
    saves.sort(key=lambda x: x.get("updated") or "", reverse=True)
    themes = []
    if store.THEMES.exists():
        for d in sorted(store.THEMES.iterdir()):
            t = store.read_json(d / "theme.json", None)
            if t:
                m = assets.manifest(d.name)
                themes.append({"slug": d.name, "name": t.get("name"), "description": t.get("description"),
                               "tone": t.get("tone"), "archetypes": t.get("archetypes", []), "stats": t.get("stats", []),
                               "resources": t.get("resources", []), "ui": t.get("ui", {}), "backdrop": t.get("menu_backdrop"),
                               "assets": len(m["assets"]), "maps": len(list((d / "maps").glob("*.json")))})
    return {"saves": saves, "themes": themes, "draft": store.draft(), "control": store.control(), "dm": store.dm_status(),
            "active": store.runtime().get("active"), "token": store.ui_token()}


def _queue(t, campaign=None, data=None, text=""):
    with store.file_lock("inbox"):
        ib = store.inbox()
        for x in ib["actions"]:
            if x.get("status") == "pending" and x.get("type") == t:
                x["status"] = "cancelled"
        a = {"id": ib["next_id"], "type": t, "text": text or t, "campaign": campaign, "data": data or {},
             "status": "pending", "created": store.now_iso()}
        ib["next_id"] += 1
        ib["actions"] = (ib["actions"] + [a])[-150:]
        store.write_json(store.INBOX, ib)
    return a


def _cancel_pending():
    with store.file_lock("inbox"):
        ib = store.inbox()
        for x in ib["actions"]:
            if x.get("status") == "pending":
                x["status"] = "cancelled"
        store.write_json(store.INBOX, ib)


def _clear_caches():
    _render.cache_clear(); _render_map.cache_clear(); assets._tpl_rows.cache_clear()


def regenerate(clear_voice=True):
    removed = 0
    if clear_voice and (store.CACHE / "tts").exists():
        removed = len(list((store.CACHE / "tts").glob("*"))); shutil.rmtree(store.CACHE / "tts", ignore_errors=True)
    _clear_caches()
    n = 0
    for d in (store.THEMES.iterdir() if store.THEMES.exists() else []):
        t = store.read_json(d / "theme.json", None)
        if not t:
            continue
        for aid, meta in assets.manifest(d.name)["assets"].items():
            try:
                svg = assets.render_recipe(d.name, {"layers": [aid]}, t.get("palette"), scale=4)
                store.write_text((d / meta["file"]).with_suffix(".svg"), svg); n += 1
            except Exception:
                pass
    from tools import build_catalog
    tpl = build_catalog.build()
    return {"assets_rerendered": n, "templates": tpl, "voice_files_cleared": removed}


def format_all():
    for d in (store.THEMES, store.CAMPAIGNS, store.CACHE):
        shutil.rmtree(d, ignore_errors=True)
    for f in (store.RUNTIME, store.INBOX, store.CONTROL, store.DMSTATUS, store.DRAFT, store.ROOT / ".browser_opened"):
        try:
            f.unlink()
        except OSError:
            pass
    for f in store.ROOT.glob(".*.lock"):
        try:
            f.unlink()
        except OSError:
            pass
    store.ensure_dirs()
    store.write_text(store.THEMES / "README.txt", "One folder per theme. Each is a reusable library (assets, maps, NPCs, lore, tables) shared by every campaign in that theme.\n")
    store.write_text(store.CAMPAIGNS / "README.txt", "One JSON file per campaign. Contains hidden DM notes - opening them spoils the story!\n")
    _clear_caches()
    store.touch()
    return {"ok": True}


def state_payload():
    rt = store.runtime()
    out = {"seq": rt["seq"], "active": rt["active"], "campaign": None, "theme": None, "map": None,
           "token": store.ui_token(), "control": store.control(), "dm": store.dm_status(),
           "pending": [a for a in store.inbox()["actions"] if a.get("status") == "pending" and a.get("campaign") == rt["active"]],
           "manners": MANNERS}
    if rt["active"]:
        c = store.read_json(store.CAMPAIGNS / f"{rt['active']}.json", None)
        if c:
            out["campaign"] = api._strip_for_ui(c)
            out["theme"] = assets.load_theme(c["theme"])
            mid = c.get("world", {}).get("map")
            if mid:
                m = assets.load_map(c["theme"], mid)
                if m:
                    out["map"] = {k: m.get(k) for k in ("id", "name", "w", "h", "rows", "backdrop")}
                    out["map"]["legend"] = {k: {"name": (v.get("name") if isinstance(v, dict) else ""),
                                                "solid": isinstance(v, dict) and v.get("solid", False)}
                                            for k, v in m["legend"].items()}
                    out["map"]["mtime"] = _mtime(assets.map_path(c["theme"], mid))
    return out


MANNERS = ["normal", "ask", "whisper", "shout", "plead", "threaten", "persuade", "lie", "joke", "sarcastic", "calm"]


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # silence (stdout is the MCP pipe when embedded)
        pass

    def _send(self, code, body, ctype="application/json", cache=False):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            self._route()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as ex:  # keep server alive
            try:
                self._send(500, json.dumps({"error": str(ex)}))
            except Exception:
                pass

    def do_POST(self):
        try:
            self._post()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as ex:
            try:
                self._send(500, json.dumps({"error": str(ex)}))
            except Exception:
                pass

    def _post(self):
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if origin and origin.split("://", 1)[-1] != host:
            return self._send(403, json.dumps({"error": "cross-origin request refused"}))
        n = int(self.headers.get("Content-Length") or 0)
        if n > 20000:
            return self._send(413, json.dumps({"error": "too large"}))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"error": "bad json"}))
        if body.get("token") != store.ui_token():
            return self._send(403, json.dumps({"error": "bad token - reload the page"}))
        path = urlparse(self.path).path
        active = store.runtime().get("active")
        if path == "/api/action":
            t = body.get("type"); text = str(body.get("text") or "").strip()
            if t not in ("speak", "do", "dm") or not text or len(text) > 2000 or not active:
                return self._send(400, json.dumps({"error": "invalid action (or no active campaign)"}))
            a = {"type": t, "text": text, "campaign": active, "status": "pending", "created": store.now_iso()}
            if t == "speak":
                a["manner"] = (str(body.get("manner") or "normal").strip() or "normal")[:30]
                a["target"] = str(body.get("target") or "").strip()[:60]
            with store.file_lock("inbox"):
                ib = store.inbox()
                if t != "dm" and any(x.get("status") == "pending" and x.get("type") in ("speak", "do") and x.get("campaign") == active
                                     for x in ib["actions"]):
                    return self._send(409, json.dumps({"error": "An action is already waiting - cancel it to change it."}))
                a["id"] = ib["next_id"]; ib["next_id"] += 1
                ib["actions"] = (ib["actions"] + [a])[-150:]
                store.write_json(store.INBOX, ib)
            return self._send(200, json.dumps({"ok": True, "action": a}))
        if path == "/api/action/cancel":
            with store.file_lock("inbox"):
                ib = store.inbox(); hit = False
                for x in ib["actions"]:
                    if x.get("id") == body.get("id") and x.get("status") == "pending":
                        x["status"] = "cancelled"; hit = True
                store.write_json(store.INBOX, ib)
            return self._send(200 if hit else 409, json.dumps({"ok": hit, "error": None if hit else "already taken by the DM"}))
        menu_only = lambda: store.runtime().get("active") is None
        J = lambda code, obj: self._send(code, json.dumps(obj))
        if path == "/api/settings":
            ctl = store.control()
            for k, cast in (("voice", bool), ("volume", float), ("text_speed", str), ("mode", str), ("paused", bool)):
                if k in body:
                    ctl[k] = cast(body[k])
            if ctl.get("mode") not in ("live", "nudge"):
                ctl["mode"] = "live"
            ctl["volume"] = max(0.0, min(1.0, float(ctl.get("volume", 0.9))))
            store.write_json(store.CONTROL, ctl)
            return J(200, {"ok": True, "control": ctl})
        if path == "/api/load":
            cid = body.get("id")
            if not (store.CAMPAIGNS / f"{cid}.json").exists():
                return J(404, {"error": "save not found"})
            _cancel_pending()
            store.set_active(cid)
            _queue("resume", cid, {"campaign": cid}, "resume campaign")
            store.set_loading("Waiting for the DM to pick up the story...", None)
            return J(200, {"ok": True})
        if path == "/api/quit":
            _cancel_pending()
            store.set_dm_status(None, loading=None, input={"enabled": True, "hint": ""})
            store.set_active(None)
            return J(200, {"ok": True})
        if path == "/api/delete_save":
            if not menu_only():
                return J(409, {"error": "Only available from the main menu."})
            p = store.CAMPAIGNS / f"{body.get('id')}.json"
            if p.exists() and p.parent == store.CAMPAIGNS:
                p.unlink(); store.touch()
                return J(200, {"ok": True})
            return J(404, {"error": "save not found"})
        if path == "/api/roll":
            try:
                return J(200, dice.roll(str(body.get("expr") or "4d6kh3")))
            except ValueError as ex:
                return J(400, {"error": str(ex)})
        if path == "/api/draft":
            with store.file_lock("draft"):
                d = body.get("draft") or {}
                cur = store.draft()
                for k in ("theme_status", "theme_note"):  # owned by DM/server
                    if k in cur and k not in d:
                        d[k] = cur[k]
                store.write_json(store.DRAFT, d)
            return J(200, {"ok": True})
        if path == "/api/wizard/build_theme":
            desc = str(body.get("description") or "").strip()
            if not desc:
                return J(400, {"error": "Describe the theme first."})
            data = {"description": desc[:2000], "mood": str(body.get("mood") or "")[:300], "base": body.get("base") or None}
            _queue("build_theme", None, data, "build theme")
            store.update_draft({"theme_status": "building", "theme_request": data})
            store.set_loading("The DM is building your world...", None)
            return J(200, {"ok": True})
        if path == "/api/wizard/cancel_build":
            with store.file_lock("inbox"):
                ib = store.inbox()
                for x in ib["actions"]:
                    if x.get("status") == "pending" and x.get("type") == "build_theme":
                        x["status"] = "cancelled"
                store.write_json(store.INBOX, ib)
            store.update_draft({"theme_status": None}); store.set_loading(done=True)
            return J(200, {"ok": True})
        if path == "/api/wizard/begin":
            d = body.get("draft") or store.draft()
            try:
                cid = api.campaign_from_wizard(d)
            except api.DMError as ex:
                return J(400, {"error": str(ex)})
            _queue("new_game", cid, {"campaign": cid, "party": d.get("party"), "notes": d.get("dm_notes_extra", "")}, "new game")
            store.set_loading("The DM is writing your story...", 5)
            try:
                store.DRAFT.unlink()
            except OSError:
                pass
            return J(200, {"ok": True, "campaign": cid})
        if path == "/api/regenerate":
            if not menu_only():
                return J(409, {"error": "Only available from the main menu."})
            return J(200, {"ok": True, **regenerate(bool(body.get("voice", True)))})
        if path == "/api/format":
            if not menu_only():
                return J(409, {"error": "Only available from the main menu."})
            if body.get("confirm") != "FORMAT":
                return J(400, {"error": "Type FORMAT to confirm."})
            return J(200, format_all())
        if path == "/api/control":
            ctl = store.control()
            if body.get("mode") in ("live", "nudge"):
                ctl["mode"] = body["mode"]
            if "paused" in body:
                ctl["paused"] = bool(body["paused"])
            store.write_json(store.CONTROL, ctl)
            return self._send(200, json.dumps({"ok": True, "control": ctl}))
        return self._send(404, json.dumps({"error": "not found"}))

    def _route(self):
        u = urlparse(self.path); q = parse_qs(u.query); path = unquote(u.path)
        if path in ("/", "/index.html"):
            return self._file(os.path.join(WEB, "index.html"))
        if path.startswith("/web/"):
            f = os.path.normpath(os.path.join(WEB, path[5:]))
            if not f.startswith(WEB):
                return self._send(403, "{}")
            return self._file(f)
        if path == "/api/state":
            return self._send(200, json.dumps(state_payload()))
        if path == "/api/menu":
            return self._send(200, json.dumps(menu_payload()))
        if path == "/api/events":
            since = int(q.get("since", ["0"])[0]); rt = store.runtime()
            return self._send(200, json.dumps({"seq": rt["seq"], "events": [e for e in rt["events"] if e["seq"] > since]}))
        if path == "/api/stream":
            return self._stream()
        if path.startswith("/r/") and path.endswith(".svg"):
            theme = path[3:-4]
            rj = q.get("r", ["{}"])[0]
            svg = _render(theme, rj, q.get("e", [""])[0], _ver(theme))
            return self._send(200, svg, "image/svg+xml", cache=True)
        if path.startswith("/part/") and path.endswith(".svg"):
            theme, ref = path[6:-4].split("/", 1)
            rec = {"layers": [{"part": ref, "colors": json.loads(q.get("c", ["{}"])[0])}]}
            svg = _render(theme, json.dumps(rec, sort_keys=True), "", _ver(theme))
            return self._send(200, svg, "image/svg+xml", cache=True)
        if path == "/tts":
            try:
                v = tts.norm_voice({"voice": q.get("v", [""])[0], "rate": q.get("r", [""])[0], "pitch": q.get("p", [""])[0]})
                f = tts.synth(q.get("t", [""])[0], v["voice"], v["rate"], v["pitch"])
                with open(f, "rb") as fh:
                    return self._send(200, fh.read(), "audio/mpeg", cache=True)
            except ImportError:
                return self._send(503, json.dumps({"error": "edge-tts not installed - rerun setup.bat"}))
            except Exception as ex:
                return self._send(502, json.dumps({"error": f"tts failed: {ex}"}))
        if path.startswith("/map/") and path.endswith(".svg"):
            theme, mid = path[5:-4].split("/", 1)
            svg = _render_map(theme, mid, _ver(theme) + _mtime(assets.map_path(theme, mid)))
            return self._send(200 if svg else 404, svg or "", "image/svg+xml")
        return self._send(404, json.dumps({"error": "not found"}))

    def _file(self, f):
        if not os.path.isfile(f):
            return self._send(404, "not found", "text/plain")
        ctype = mimetypes.guess_type(f)[0] or "application/octet-stream"
        if f.endswith(".js"):
            ctype = "text/javascript"
        with open(f, "rb") as fh:
            self._send(200, fh.read(), ctype + ("; charset=utf-8" if ctype.startswith("text") else ""))

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        last_m, last_seq, t0 = -1, -1, time.time()
        self.wfile.write(b"retry: 1000\n\n"); self.wfile.flush()
        while True:
            m = _mtime(store.RUNTIME)
            rt = store.runtime()
            act = rt.get("active")
            cm = _mtime(store.CAMPAIGNS / f"{act}.json") if act else 0
            key = (m, cm, _mtime(store.INBOX), _mtime(store.CONTROL), _mtime(store.DMSTATUS), _mtime(store.DRAFT),
                   _mtime(store.CAMPAIGNS))
            if key != last_m:
                last_m = key
                if rt["seq"] != last_seq or True:
                    last_seq = rt["seq"]
                    self.wfile.write(f"data: {json.dumps({'seq': rt['seq']})}\n\n".encode()); self.wfile.flush()
            elif time.time() - t0 > 15:
                t0 = time.time(); self.wfile.write(b": ping\n\n"); self.wfile.flush()
            time.sleep(0.2)


def port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def make_server(host=None, port=None):
    cfg = store.config()
    host = host or cfg["ui_host"]; port = port or cfg["ui_port"]
    srv = ThreadingHTTPServer((host, port), H)
    srv.daemon_threads = True
    return srv


def start_in_thread():
    """Start the UI server in a daemon thread unless something already listens on the port. Returns URL."""
    cfg = store.config()
    url = f"http://{cfg['ui_host']}:{cfg['ui_port']}/"
    if port_in_use(cfg["ui_host"], cfg["ui_port"]):
        return url
    srv = make_server()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return url


if __name__ == "__main__":
    store.ensure_dirs()
    cfg = store.config()
    srv = make_server()
    url = f"http://{cfg['ui_host']}:{cfg['ui_port']}/"
    print(f"Claude DnD UI running at {url}  (Ctrl+C to stop)")
    if cfg.get("open_browser") and "--no-browser" not in sys.argv:
        import webbrowser; webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
