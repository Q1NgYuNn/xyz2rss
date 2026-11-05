#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小宇宙 -> RSS 的 HTTP 服务（给 iOS 快捷方式调用）。

    python3 server.py [--port 8788]

接口：
    GET /rss?url=<小宇宙链接>
        200 text/xml               —— RSS 正文
    GET /api/convert?url=<链接>
        200 application/json       —— {ok, title, episodes, rss, pid}
    GET /api/health
"""
import argparse
import json
import sys
import os
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B
import core

CACHE = {}
CACHE_TTL = 600


def convert(url):
    import time
    key = url.strip()
    hit = CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    xml, info = B.build(url, verbose=False)
    result = {"xml": xml, "info": info}
    CACHE[key] = (time.time(), result)
    return result


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 静音
        pass

    def _send(self, code, body, ctype="text/plain; charset=utf-8", extra=None):
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=300")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        target = (qs.get("url") or qs.get("u") or [""])[0].strip()

        if parsed.path == "/api/health":
            return self._send(200, json.dumps({"ok": True}), "application/json")

        if parsed.path not in ("/rss", "/api/convert"):
            return self._send(404, "not found")

        if not target:
            return self._send(400, json.dumps(
                {"ok": False, "error": "缺少 url 参数"}, ensure_ascii=False),
                "application/json")

        try:
            res = convert(target)
        except core.XyzError as e:
            return self._send(502, json.dumps(
                {"ok": False, "error": str(e)}, ensure_ascii=False), "application/json")
        except Exception:  # noqa
            traceback.print_exc()
            return self._send(500, json.dumps(
                {"ok": False, "error": "内部错误"}, ensure_ascii=False), "application/json")

        info = res["info"]
        if parsed.path == "/rss":
            return self._send(200, res["xml"], "application/rss+xml; charset=utf-8")

        return self._send(200, json.dumps({
            "ok": True,
            "title": info.get("title"),
            "pid": info.get("pid"),
            "source": info.get("source"),
            "episodes": info.get("episodes"),
            "declared": info.get("declared"),
            "rss": "http://%s/rss?url=%s" % (
                self.headers.get("Host", "127.0.0.1"),
                urllib.parse.quote(target, safe="")),
        }, ensure_ascii=False), "application/json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print("listening on http://%s:%d" % (a.host, a.port), file=sys.stderr, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
