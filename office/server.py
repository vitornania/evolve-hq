#!/usr/bin/env python3
"""Serve Evolve HQ and its workspace activity on this Mac."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import subprocess
from urllib.parse import parse_qs, unquote, urlsplit

from activity import ROOT, snapshot
from advisor import MAX_CHAT_BYTES, respond_to_chat
from cpa import calculate_cpa
from learning import change as change_memory, dashboard as memory_dashboard
from learning_replay import start_worker
from providers import status as provider_status
from skill_runs import MAX_REQUEST_BYTES, RUN_LOCK, get_run, start_run
from static_preview import render_preview
from workflow_batches import workflow_catalog

DEFAULT_PORT = 8739
OFFICE = Path(__file__).resolve().parent
THREE = ROOT / "node_modules/three"
PAGES = {"/": "office", "/workflows": "workbench", "/local-tools": "local", "/memory": "workbench"}
CONTENT_TYPES = {".html": "text/html", ".md": "text/plain", ".css": "text/css",
                 ".js": "text/javascript", ".json": "application/json", ".woff2": "font/woff2"}
FILES = {
    "/": OFFICE / "index.html",
    "/style.css": OFFICE / "style.css",
    "/app.js": OFFICE / "app.js",
    "/scene.js": OFFICE / "scene.js",
    "/catalog.json": ROOT / "team/catalog.json",
    "/workflows": OFFICE / "workbench.html",
    "/workbench.css": OFFICE / "workbench.css",
    "/workbench.js": OFFICE / "workbench.js",
    "/memory": OFFICE / "memory.html",
    "/memory.js": OFFICE / "memory.js",
    "/static-libraries.js": OFFICE / "static-libraries.js",
    "/advisor.js": OFFICE / "advisor.js",
    "/header.css": OFFICE / "header.css",
    "/skill-guide.json": ROOT / "team/skill-guide.json",
    "/fonts/geist.woff2": ROOT / "node_modules/@fontsource-variable/geist/files/geist-latin-wght-normal.woff2",
    "/local-tools": ROOT / "index.html",
    "/cpa-calculator.js": OFFICE / "cpa-calculator.js",
    "/team/roster.md": ROOT / "team/roster.md",
    "/setup-guide": ROOT / "docs/SETUP.md",
    "/three/build/three.module.js": THREE / "build/three.module.js",
    "/three/build/three.core.js": THREE / "build/three.core.js",
    "/three/addons/controls/OrbitControls.js": THREE / "examples/jsm/controls/OrbitControls.js",
}
POST_ROUTES = {
    "/api/run": (start_run, MAX_REQUEST_BYTES, 202),
    "/api/advisor": (respond_to_chat, MAX_CHAT_BYTES, 200),
    "/api/cpa": (calculate_cpa, 4096, 200),
    "/api/static-preview": (render_preview, 4096, 200),
    "/api/memory": (lambda payload: change_memory(ROOT, payload), 4096, 200),
}


def page_content(path, file):
    html = file.read_text(encoding="utf-8")
    header = (OFFICE / "header.html").read_text(encoding="utf-8").strip()
    for page in PAGES.values():
        header = header.replace("{{" + page + "}}", ' aria-current="page"' if page == PAGES[path] else "")
    html = re.sub(r"<!-- HQ_HEADER_START -->.*?<!-- HQ_HEADER_END -->", "<!-- HQ_HEADER -->", html, count=1, flags=re.S)
    return html.replace("<!-- HQ_HEADER -->", header, 1).replace(
        "</head>", '<link rel="stylesheet" href="/header.css">\n</head>', 1).encode()


class Handler(BaseHTTPRequestHandler):
    def local_host(self):
        port = self.server.server_port
        host = self.headers.get("Host")
        return host if host in {f"127.0.0.1:{port}", f"localhost:{port}"} else None

    def json_response(self, data, status=200):
        self.respond(json.dumps(data).encode(), "application/json", status)

    def respond(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.local_host():
            self.send_error(403)
            return
        target = urlsplit(self.path)
        path = unquote(target.path)
        if path == "/api/run":
            identifier = parse_qs(target.query).get("id", [""])[0]
            data = get_run(identifier)
            self.json_response(data or {"error": "Run not found."}, 200 if data else 404)
            return
        if path == "/api/run-video-frame":
            params = parse_qs(target.query)
            identifier = params.get("id", [""])[0]
            name = params.get("frame", [""])[0]
            if re.fullmatch(r"(?:prior-)?video-frame-0[1-8]\.jpg", name):
                data = get_run(identifier)
                field = "previousVideo" if name.startswith("prior-") else "video"
                video = (data or {}).get(field) or {}
                folder = (ROOT / "tasks" / identifier).resolve()
                picture = folder / name
                if (any(frame["file"] == name for frame in video.get("frames", []))
                        and picture.is_file() and not picture.is_symlink()):
                    self.respond(picture.read_bytes(), "image/jpeg")
                    return
            self.send_error(404)
            return
        if path == "/api/providers":
            self.json_response(provider_status())
            return
        if path == "/api/memory":
            try:
                self.json_response(memory_dashboard(ROOT))
            except (sqlite3.Error, OSError):
                self.json_response({"error": "Local memory is temporarily unavailable."}, 503)
            return
        if path == "/api/workflows":
            self.json_response(workflow_catalog())
            return
        if path == "/api/static-libraries":
            config = ROOT / ".office/static-libraries.json"
            try:
                links = json.loads(config.read_text(encoding="utf-8")) if config.is_file() else []
            except (OSError, ValueError):
                links = []
            self.json_response(links if isinstance(links, list) else [])
            return
        if path == "/api/activity":
            try:
                self.respond(json.dumps(snapshot()).encode(), "application/json")
            except (sqlite3.Error, OSError) as error:
                self.log_error("Activity read failed: %s", error)
                self.respond(b'{"error":"Activity temporarily unavailable"}', "application/json", 503)
            return
        file = FILES.get(path)
        if file is None and path.startswith("/tasks/") and path.endswith("/RECORD.md"):
            candidate = (ROOT / path.lstrip("/")).resolve()
            if candidate.is_relative_to(ROOT / "tasks"):
                file = candidate
        if file is None or not file.is_file():
            self.send_error(404)
            return
        content_type = CONTENT_TYPES.get(file.suffix, "application/octet-stream")
        if path in PAGES:
            self.respond(page_content(path, file), "text/html; charset=utf-8")
        elif file.suffix == ".woff2":
            self.respond(file.read_bytes(), "font/woff2")
        else:
            self.respond(file.read_bytes(), content_type + "; charset=utf-8")

    def do_POST(self):
        host = self.local_host()
        if not host or self.headers.get("Origin") != f"http://{host}":
            self.json_response({"error": "Open the local Evolve HQ page to send this request."}, 403)
            return
        route = POST_ROUTES.get(self.path)
        if not route:
            self.send_error(404)
            return
        action, limit, success_status = route
        if self.headers.get_content_type() != "application/json":
            self.json_response({"error": "Expected a JSON request."}, 415)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= limit:
                self.json_response({"error": "The request is too large or empty."}, 413)
                return
            payload = json.loads(self.rfile.read(size))
            self.json_response(action(payload), success_status)
        except (UnicodeError, json.JSONDecodeError):
            self.json_response({"error": "Could not read the request."}, 400)
        except ValueError as error:
            self.json_response({"error": str(error)}, 400)
        except RuntimeError as error:
            self.json_response({"error": str(error)}, 409 if self.path == "/api/run" else 503)
        except (OSError, sqlite3.Error) as error:
            self.log_error("Request failed: %s", error)
            self.json_response({"error": "Evolve HQ couldn’t complete the request. Try again."}, 503)

    def log_message(self, fmt, *args):
        if not (self.path == "/api/activity" and len(args) > 1 and args[1] == "200"):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    if not FILES["/three/build/three.module.js"].is_file():
        parser.exit(1, "Install the local scene dependency with npm ci.\n")
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Evolve HQ · {url}", flush=True)
        if args.open:
            import webbrowser
            webbrowser.open(url)
        stop_learning = start_worker(ROOT, RUN_LOCK.locked)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop_learning.set()


if __name__ == "__main__":
    main()
