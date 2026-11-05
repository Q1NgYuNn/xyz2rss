#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把小宇宙播客发布成 GitHub Pages 上的静态 RSS。

设计：
  feeds/<slug>.xml          —— 每个播客一个固定地址（slug 由 pid 决定，永不变）
  feeds/index.json          —— 清单，记录 pid/title/发布时间
  docs/                     —— GitHub Pages 根目录（feeds 输出到这里）

RSS 地址形如： https://<user>.github.io/<repo>/<slug>.xml
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B
import core

DOCS = os.path.join(HERE, "docs")
INDEX = os.path.join(DOCS, "index.json")


def load_index():
    try:
        with open(INDEX, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa
        return {"feeds": {}}


def save_index(idx):
    os.makedirs(DOCS, exist_ok=True)
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)


def publish(url, quiet=False):
    xml, info = B.build(url, verbose=not quiet)
    pid = info["pid"]
    slug = pid  # pid 天然唯一且稳定
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, "%s.xml" % slug)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)

    idx = load_index()
    idx["feeds"][slug] = {
        "pid": pid,
        "title": info.get("title"),
        "source": info.get("source"),
        "episodes": info.get("episodes"),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file": "%s.xml" % slug,
    }
    save_index(idx)
    return slug, info, len(xml)


def git_publish(message, repo_url=None):
    """在 docs 所在仓库提交并推送。"""
    cmds = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", message],
        ["git", "push"],
    ]
    out = []
    for c in cmds:
        r = subprocess.run(c, cwd=HERE, capture_output=True, text=True)
        out.append((c[0] + " " + (c[1] if len(c) > 1 else ""), r.returncode,
                    (r.stdout + r.stderr).strip()[-400:]))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    a = ap.parse_args()
    slug, info, n = publish(a.url)
    print(json.dumps({"slug": slug, **info, "bytes": n}, ensure_ascii=False))
