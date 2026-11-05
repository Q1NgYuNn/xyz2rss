#!/bin/sh
# 一键部署到 GitHub Pages
#   export GITHUB_PAT=xxx
#   ./deploy.sh <github-username> [repo-name]
set -e

USER="${1:-}"
REPO="${2:-xyz2rss}"
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE"

if [ -z "$USER" ]; then
  echo "用法: ./deploy.sh <github-username> [repo-name]" >&2
  exit 2
fi
if [ -z "$GITHUB_PAT" ]; then
  echo "缺少环境变量 GITHUB_PAT（GitHub Personal Access Token，需 repo 权限）" >&2
  exit 2
fi

API="https://api.github.com"
AUTH="Authorization: Bearer $GITHUB_PAT"

echo "==> 1/6 检查账号"
curl -sS -H "$AUTH" "$API/user" -o /tmp/ghme.json
ME=$(python3 -c "import json;print(json.load(open('/tmp/ghme.json')).get('login',''))")
[ -n "$ME" ] || { echo "token 无效：$(head -c 200 /tmp/ghme.json)"; exit 1; }
echo "    登录为: $ME"

echo "==> 2/6 创建仓库 $REPO"
curl -sS -X POST -H "$AUTH" -H "Accept: application/vnd.github+json" \
  "$API/user/repos" \
  -d "{\"name\":\"$REPO\",\"private\":false,\"auto_init\":false,\"description\":\"小宇宙播客 → RSS\"}" \
  -o /tmp/ghrepo.json -w '%{http_code}\n' | tail -1

echo "==> 3/6 推送代码"
if [ ! -d .git ]; then
  git init -q
  git checkout -q -b main 2>/dev/null || git branch -M main
fi
git add -A
git -c user.name="xyz2rss" -c user.email="xyz2rss@users.noreply.github.com" \
    commit -q -m "init: xiaoyuzhou → rss" || echo "    (无变更)"
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:$GITHUB_PAT@github.com/$ME/$REPO.git"
git push -u origin main --force -q
echo "    已推送"

echo "==> 4/6 开启 GitHub Pages（main 分支 /docs）"
curl -sS -X POST -H "$AUTH" -H "Accept: application/vnd.github+json" \
  "$API/repos/$ME/$REPO/pages" \
  -d '{"source":{"branch":"main","path":"/docs"}}' \
  -o /tmp/ghpages.json -w '    %{http_code}\n'

echo "==> 5/6 等待 Pages 生效"
for i in 1 2 3 4 5 6 7 8 9 10; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "https://$ME.github.io/$REPO/heartbeat.txt" || true)
  [ "$CODE" = "200" ] && break
  sleep 6
done

echo "==> 6/6 完成"
echo ""
echo "  RSS 目录:  https://$ME.github.io/$REPO/"
echo "  转换接口:  https://$ME.github.io/$REPO/api/convert  (静态站不支持，需自建 server.py)"
echo ""
python3 - <<EOF
import json
try:
    idx=json.load(open('docs/index.json'))
    for slug,m in idx.get('feeds',{}).items():
        print("  《%s》 → https://$ME.github.io/$REPO/%s.xml  (%s 集)" % (m.get('title'),slug,m.get('episodes')))
except Exception:
    pass
EOF
