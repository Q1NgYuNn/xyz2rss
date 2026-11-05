#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模拟「纯快捷指令」的完整逻辑，用于验证可行性。

快捷指令里的动作序列：
  1. 接收分享输入 / 读剪贴板
  2. 匹配文本 -> pid
  3. 获取 URL 内容 -> 播客页 HTML
  4. 匹配文本 -> 播客标题
  5. 获取 URL 内容 -> itunes search?term=<标题>
  6. 从 JSON 取 results 中 collectionName == 标题 的 feedUrl
  7. 有 feedUrl -> 直接返回（官方完整 RSS）
     无 feedUrl -> 用播客页数据拼 RSS，写入 GitHub，返回仓库地址
"""
import json
import re
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def step2_pid(text):
    m = re.search(r"xiaoyuzhoufm\.com/podcast/([0-9a-f]{24})", text)
    if m:
        return m.group(1)
    m = re.search(r"([0-9a-f]{24})", text)
    return m.group(1) if m else None


def step4_title(html):
    m = re.search(r'"podcast":\{"type":"PODCAST","pid":"[0-9a-f]{24}","title":"(.*?)"', html)
    if m:
        return m.group(1)
    m = re.search(r'<title>(.*?)</title>', html)
    return m.group(1).split("|")[0].strip() if m else None


def step6_feed(title):
    url = ("https://itunes.apple.com/search?term=%s&entity=podcast&country=cn&limit=15"
           % urllib.parse.quote(title))
    d = json.loads(get(url))
    for r in d.get("results", []):
        if (r.get("collectionName") or "").strip() == title and r.get("feedUrl"):
            return r["feedUrl"]
    return None


def run(link):
    pid = step2_pid(link)
    if not pid:
        return {"ok": False, "error": "认不出链接"}
    html = get("https://www.xiaoyuzhoufm.com/podcast/%s" % pid)
    title = step4_title(html)
    if not title:
        return {"ok": False, "error": "读不到播客标题"}
    feed = step6_feed(title)
    if feed:
        return {"ok": True, "mode": "official", "title": title, "rss": feed}
    return {"ok": True, "mode": "need-build", "title": title, "pid": pid,
            "note": "无官方 feed，需拼装 RSS"}


if __name__ == "__main__":
    import sys
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False, indent=2))
