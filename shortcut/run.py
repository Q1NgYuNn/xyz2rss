#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快捷方式「小宇宙 → RSS」的执行核心。

iOS 快捷方式无法运行 Python，所以在真实快捷方式里这一步由两步 HTTP 完成：
  1) Get Contents of URL  ->  <SERVER>/api/convert?url=<输入>
  2) Get Dictionary Value ->  rss

本脚本用于本地/服务端模拟同一套逻辑，方便测试快捷方式行为。
"""
import json
import urllib.error
import sys
import urllib.parse
import urllib.request


def convert(server, link):
    try:
        return _convert(server, link)
    except Exception as e:  # noqa
        raise RuntimeError(str(e).replace("HTTP 404", "这个播客不存在（404）"))


def _convert(server, link):
    q = "%s/api/convert?url=%s" % (server.rstrip("/"), urllib.parse.quote(link, safe=""))
    req = urllib.request.Request(q, headers={"User-Agent": "Shortcuts/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
            msg = data.get("error") or ("HTTP %s" % e.code)
        except Exception:  # noqa
            msg = "HTTP %s" % e.code
        raise RuntimeError(msg)
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "转换失败")
    return data


if __name__ == "__main__":
    server = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8788"
    link = sys.argv[2] if len(sys.argv) > 2 else input("粘贴小宇宙链接：").strip()
    d = convert(server, link)
    print("《%s》 %s 集（共 %s 集）" % (d["title"], d["episodes"], d.get("declared")))
    print(d["rss"])
