#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小宇宙播客 -> RSS 生成器（CLI）。

    python3 build.py <链接> [-o out.xml] [--limit N] [--no-paid] [--no-cache]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache")


def cache_path(pid):
    return os.path.join(CACHE_DIR, "%s.json" % pid)


def load_cache(pid):
    try:
        with open(cache_path(pid), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa
        return None


def save_cache(pid, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = cache_path(pid) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, cache_path(pid))


def build(url, limit=0, include_paid=True, verbose=True, deep=False):
    """返回 (xml, info)。info 说明数据来源与集数。"""
    pid = core.resolve(url)
    pod = core.load_podcast(pid)
    info = {"pid": pid, "title": pod.get("title"), "declared": pod.get("episodeCount")}

    # ---- 策略 A：官方完整 feed
    feed = core.find_official_feed(pod)
    if feed:
        try:
            opod, oeps, _meta = core.fetch_official_feed(feed)
            for k in ("title", "author", "description", "image"):
                if opod.get(k):
                    pod[k] = opod[k]
            pod["link"] = opod.get("link") or pod.get("_source_url")
            info.update(source="official", feed=feed, episodes=len(oeps))
            if verbose:
                print("[official] %s  %d 集  %s" % (pod.get("title"), len(oeps), feed),
                      file=sys.stderr)
            return core.render_rss(pod, oeps, limit=limit, include_paid=include_paid), info
        except core.XyzError as e:
            if verbose:
                print("[warn] 官方 feed 失败：%s" % e, file=sys.stderr)

    # ---- 策略 B：网页最新一页 + 本地累积缓存
    eps = list(pod.get("episodes") or [])
    cached = load_cache(pid) or {}
    known = {e["eid"]: e for e in cached.get("episodes", [])}
    added = 0
    for e in eps:
        if e["eid"] not in known:
            known[e["eid"]] = e
            added += 1
    merged = list(known.values())

    # ---- 可选：逐集补齐详情（慢，--deep）
    if deep:
        for e in list(merged):
            if not e.get("shownotes"):
                try:
                    d = core.episode_detail(e["eid"])
                    e.update({k: d[k] for k in
                              ("shownotes", "description", "duration", "media",
                               "enclosure", "payType") if k in d})
                except Exception:  # noqa
                    pass

    save_cache(pid, {"pid": pid, "title": pod.get("title"),
                     "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "episodes": merged})
    info.update(source="web", episodes=len(merged), new=added)
    if verbose:
        print("[web] %s  本次 %d 集 / 累计 %d 集" % (pod.get("title"), len(eps), len(merged)),
              file=sys.stderr)
    return core.render_rss(pod, merged, limit=limit, include_paid=include_paid), info


def main():
    ap = argparse.ArgumentParser(description="小宇宙播客 -> RSS")
    ap.add_argument("url")
    ap.add_argument("-o", "--out", default="-")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-paid", action="store_true")
    ap.add_argument("--deep", action="store_true", help="逐集抓详情补全简介（慢）")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args()

    xml, info = build(a.url, limit=a.limit, include_paid=not a.no_paid,
                      verbose=not a.quiet, deep=a.deep)
    if a.out == "-":
        sys.stdout.write(xml)
    else:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(xml)
        if not a.quiet:
            print("-> %s (%d bytes, %d 集)" % (a.out, len(xml), info.get("episodes")),
                  file=sys.stderr)


if __name__ == "__main__":
    main()
