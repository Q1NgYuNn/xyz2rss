#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键添加：小宇宙链接 -> 生成 RSS -> 推送到 GitHub Pages。

    export GITHUB_PAT=xxx
    python3 add.py "<小宇宙链接>" [更多链接...]

token 只从环境变量读取，不写入任何文件、不进入网页。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import publish


def git(args):
    r = subprocess.run(args, cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stdout + r.stderr).strip()[-500:])
    return r.stdout


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    if not os.environ.get("GITHUB_PAT"):
        print("缺少环境变量 GITHUB_PAT", file=sys.stderr)
        return 2

    results = []
    published = []
    for url in argv:
        try:
            slug, info, size = publish.publish(url)
            results.append((True, info.get("title"), info.get("episodes"),
                            info.get("source"), info.get("declared")))
            published.append((slug, info.get("title"), info.get("episodes"),
                              info.get("source"), info.get("declared")))
            print("[ok] 《%s》 %s 集（共 %s）来源=%s"
                  % (info.get("title"), info.get("episodes"),
                     info.get("declared"), info.get("source")))
        except Exception as e:  # noqa
            results.append((False, url, None, None, None))
            print("[fail] %s -> %s" % (url, e), file=sys.stderr)

    if not any(r[0] for r in results):
        print("全部失败，未推送", file=sys.stderr)
        return 1

    git(["git", "add", "docs"])
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=HERE)
    if r.returncode == 0:
        print("内容无变化，无需推送")
        return 0

    names = "、".join(r[1] for r in results if r[0])
    git(["git", "-c", "user.name=xyz2rss",
         "-c", "user.email=xyz2rss@users.noreply.github.com",
         "commit", "-q", "-m", "feed: %s" % names])
    git(["git", "push", "-q"])
    print("\n已推送。约 1 分钟后生效：")
    for pid, title, eps, src, declared in published:
        print("  《%s》 %s 集  ->  https://q1ngyunn.github.io/xyz2rss/%s.xml"
              % (title, eps, pid))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
