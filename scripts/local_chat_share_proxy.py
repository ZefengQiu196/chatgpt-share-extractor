#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5500,"
    "http://127.0.0.1:5500,"
    "http://localhost:5501,"
    "http://127.0.0.1:5501,"
    "http://localhost:8000,"
    "http://127.0.0.1:8000"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local CORS proxy for fetching ChatGPT share page HTML."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host, default 127.0.0.1.")
    parser.add_argument("--port", type=int, default=8787, help="Bind port, default 8787.")
    parser.add_argument(
        "--allowed-origins",
        default=DEFAULT_ALLOWED_ORIGINS,
        help='Comma-separated origins. Use "*" to allow any origin.',
    )
    parser.add_argument("--timeout", type=int, default=35, help="Upstream timeout seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Retries per upstream URL.")
    return parser.parse_args()


def parse_allowed_origins(raw: str) -> set[str] | None:
    text = (raw or "").strip()
    if not text or text == "*":
        return None
    return {item.strip() for item in text.split(",") if item.strip()}


def build_headers(origin: str | None, allowed: set[str] | None) -> dict[str, str]:
    if allowed is None:
        allow_origin = "*"
    elif origin and origin in allowed:
        allow_origin = origin
    elif allowed:
        allow_origin = sorted(allowed)[0]
    else:
        allow_origin = "*"
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
    }


def is_allowed_origin(origin: str | None, allowed: set[str] | None) -> bool:
    if allowed is None:
        return True
    if not origin:
        return True
    return origin in allowed


def is_allowed_share_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:  # noqa: BLE001
        return False
    if parsed.scheme != "https":
        return False
    if parsed.hostname != "chatgpt.com":
        return False
    if not parsed.path.startswith("/share/"):
        return False
    if parsed.username or parsed.password:
        return False
    return True


def build_alt_url(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname != "chatgpt.com" or not parsed.path.startswith("/share/"):
        return None
    return urllib.parse.urlunparse(
        (
            parsed.scheme,
            "chat.openai.com",
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def upstream_candidates(url: str) -> list[str]:
    out = [url]
    alt = build_alt_url(url)
    if alt:
        out.append(alt)
    return out


def build_upstream_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://chatgpt.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )


def fetch_html(url: str, retries: int, timeout: int) -> tuple[int, str]:
    context = ssl.create_default_context()
    candidates = upstream_candidates(url)
    for idx, candidate in enumerate(candidates):
        last_status = 502
        last_text = "upstream_fetch_failed"
        for _ in range(max(retries, 1)):
            try:
                req = build_upstream_request(candidate)
                with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                    text = resp.read().decode("utf-8", errors="replace")
                    if 200 <= resp.status < 300:
                        return 200, text
                    last_status = int(resp.status)
                    last_text = text
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                last_status = int(exc.code)
                last_text = body
            except Exception as exc:  # noqa: BLE001
                last_status = 502
                last_text = f"upstream_fetch_failed: {exc}"
        if last_status != 403:
            return last_status, last_text
        if idx == len(candidates) - 1:
            return last_status, last_text
    return 502, "upstream_fetch_failed"


class ProxyHandler(BaseHTTPRequestHandler):
    allowed_origins: set[str] | None = None
    timeout: int = 35
    retries: int = 3

    def do_OPTIONS(self) -> None:  # noqa: N802
        headers = build_headers(self.headers.get("Origin"), self.allowed_origins)
        self.send_response(204)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        origin = self.headers.get("Origin")
        cors = build_headers(origin, self.allowed_origins)
        if not is_allowed_origin(origin, self.allowed_origins):
            self._json_response(
                403,
                {"error": "origin_not_allowed", "detail": "Origin is not allowed."},
                cors,
            )
            return

        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._json_response(200, {"ok": True}, cors)
            return

        if parsed.path != "/fetch":
            self._json_response(404, {"error": "not_found"}, cors)
            return

        query = urllib.parse.parse_qs(parsed.query)
        target = (query.get("url") or [""])[0].strip()
        if not target:
            self._json_response(400, {"error": "missing_url_param"}, cors)
            return
        if not is_allowed_share_url(target):
            self._json_response(
                400,
                {
                    "error": "target_not_allowed",
                    "detail": "Only https://chatgpt.com/share/... is allowed.",
                },
                cors,
            )
            return

        status, text = fetch_html(target, retries=self.retries, timeout=self.timeout)
        self.send_response(200 if 200 <= status < 300 else status)
        for key, value in cors.items():
            self.send_header(key, value)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8", errors="replace"))

    def _json_response(self, status: int, payload: dict[str, object], cors: dict[str, str]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        for key, value in cors.items():
            self.send_header(key, value)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def serve(host: str, port: int, allowed_origins: set[str] | None, timeout: int, retries: int) -> None:
    ProxyHandler.allowed_origins = allowed_origins
    ProxyHandler.timeout = timeout
    ProxyHandler.retries = retries
    server = ThreadingHTTPServer((host, port), ProxyHandler)
    shown = "*" if allowed_origins is None else ",".join(sorted(allowed_origins))
    print(f"[proxy] listening on http://{host}:{port}")
    print(f"[proxy] allowed origins: {shown}")
    print("[proxy] endpoint: /fetch?url=https%3A%2F%2Fchatgpt.com%2Fshare%2F...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    args = parse_args()
    allowed = parse_allowed_origins(args.allowed_origins)
    serve(
        host=args.host,
        port=args.port,
        allowed_origins=allowed,
        timeout=args.timeout,
        retries=args.retries,
    )


if __name__ == "__main__":
    main()
