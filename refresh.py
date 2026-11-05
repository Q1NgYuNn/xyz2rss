#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日刷新所有已发布 RSS 的脚本（GitHub Actions 调用）。

读取 docs/index.json 中登记的每个 pid，重新抓取并覆盖对应 xml。
官方 feed 存在的播客 => 全量刷新；否则 => 刷新最新一页并与历史合并。
"""
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import publish

DOCS = os.path.join(HERE, "docs")


def main():
    idx = publish.load_index()
    feeds = idx.get("feeds", {})
    if not feeds:
        print("没有已登记的播客，跳过")
        return 0

    ok, fail = 0, []
    for slug, meta in list(feeds.items()):
        pid = meta.get("pid") or slug
        url = "https://www.xiaoyuzhoufm.com/podcast/%s" % pid
        try:
            s, info, n = publish.publish(url, quiet=True)
            meta.update({"title": info.get("title"), "source": info.get("source"),
                         "episodes": info.get("episodes"),
                         "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            ok += 1
            print("[ok] %-22s %s 集 (%s)" % ((info.get("title") or "")[:22],
                                             info.get("episodes"), info.get("source")))
        except Exception as e:  # noqa
            fail.append(pid)
            print("[fail] %s: %s" % (pid, e))
            traceback.print_exc()
        time.sleep(1.5)  # 温和请求，避免触发风控

    publish.save_index(idx)
    print("\n成功 %d / 失败 %d" % (ok, len(fail)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
