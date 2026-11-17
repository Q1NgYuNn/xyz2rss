#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用登录态拉取播客全量单集（突破网页只给 15 集的限制）。

    export XJ_ACCESS_TOKEN=<x-jike-access-token>
    python3 fetch_all.py <pid>

只读拉取，不写账号状态。token 只从环境变量读取。
"""
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core
import publish

API = "https://api.xiaoyuzhoufm.com/v1/episode/list"


def post(url, body, token, timeout=30):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={
            "Content-Type": "application/json",
            "x-jike-access-token": token,
            "User-Agent": ("xiaoyuzhou/4.30.0 (iPhone; iOS 17.0; Scale/3.00)"),
            "Accept": "application/json",
        })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_all(pid, token, max_pages=40):
    eps, key, seen = [], None, set()
    for page in range(max_pages):
        body = {"pid": pid, "order": "desc"}
        if key:
            body["loadMoreKey"] = key
        data = post(API, body, token)
        page_eps = data.get("data") or []
        for e in page_eps:
            eid = e.get("eid")
            if eid and eid not in seen:
                seen.add(eid)
                eps.append(e)
        key = data.get("loadMoreKey")
        print("  第 %d 页 %d 条（累计 %d / 共 %s）"
              % (page + 1, len(page_eps), len(eps), data.get("total")), flush=True)
        if not key or not page_eps:
            break
        time.sleep(0.6)
    return eps


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    token = os.environ.get("XJ_ACCESS_TOKEN", "")
    if not token:
        print("缺少环境变量 XJ_ACCESS_TOKEN", file=sys.stderr)
        return 2

    pid = core.resolve(argv[0])
    pod = core.load_podcast(pid)
    print("《%s》网页公开 %d 集，开始拉全量…"
          % (pod.get("title"), len(pod.get("episodes") or [])))

    eps = fetch_all(pid, token)
    xml = core.render_rss(pod, eps)
    ok, n = core.rss_valid(xml)
    if not ok:
        print("RSS 校验失败：%s" % n, file=sys.stderr)
        return 1

    os.makedirs(publish.DOCS, exist_ok=True)
    path = os.path.join(publish.DOCS, "%s.xml" % pid)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)

    idx = publish.load_index()
    idx["feeds"][pid] = {
        "pid": pid,
        "title": pod.get("title"),
        "source": "token",
        "episodes": n,
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file": "%s.xml" % pid,
    }
    publish.save_index(idx)
    print("[ok] 《%s》 %d 集 -> docs/%s.xml（%d 字节）"
          % (pod.get("title"), n, pid, len(xml)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
