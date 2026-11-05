# 小宇宙 → RSS

把小宇宙播客链接转换成标准播客 RSS，可在 Apple Podcasts、Overcast、Pocket Casts、小宇宙（导入）等客户端订阅。

## 怎么用

### 方式一：iOS 快捷方式（推荐）

1. 安装快捷方式「小宇宙 → RSS」
2. 在小宇宙 App 里复制播客链接（分享 → 复制链接）
3. 运行快捷方式，粘贴链接
4. 会返回一个 RSS 地址，复制后在播客客户端里「通过 URL 订阅」

### 方式二：直接访问接口

```
<SERVER>/rss?url=<小宇宙链接(URL 编码)>
```

## 数据来源与局限（重要）

小宇宙网页版**只公开每个播客最新的 15 集**，没有分页接口。因此本工具分两种情形：

| 情形 | 能拿到的集数 | 说明 |
|---|---|---|
| 播客已上架 Apple Podcasts，且小宇宙托管了官方 feed | **全部** | 通过 Apple Podcasts 搜索反查到 `feed.xyzfm.space/<slug>`，直接使用官方完整 feed |
| 其他播客 | 最新 15 集 | 网页公开数据的上限，无法突破 |

生成 RSS 时会把音频地址从官方统计跳转链接改写为 `media.xyzcdn.net` 直链（已实测支持 Range 请求，可拖动进度条）。

## 自建部署

需要：一个 GitHub 账号 + 一个具有 `repo` 权限的 Personal Access Token。

```bash
# 1. 建仓库并推送
export GITHUB_PAT=你的token
./deploy.sh <你的GitHub用户名>

# 2. GitHub 仓库 Settings → Pages → Source 选 "GitHub Actions" 或 "Deploy from branch: main /docs"
```

部署后：
- RSS 地址：`https://<用户名>.github.io/xyz2rss/<pid>.xml`
- 接口地址：`https://<用户名>.github.io/xyz2rss/`（静态站点，不支持动态查询；如需动态接口请部署 `server.py` 到任意支持 Python 的主机）

### 添加/更新播客

```bash
python3 publish.py "<小宇宙链接>"   # 生成到 docs/<pid>.xml 并登记
git add docs && git commit -m "add feed" && git push
```

`refresh.py` 会遍历 `docs/index.json` 中登记的所有播客并刷新。

## 本地运行

```bash
python3 server.py --port 8788          # 启动转换接口
python3 build.py "<链接>" -o out.xml    # 直接生成
```

无任何第三方依赖，Python 3.8+ 即可。

## 文件说明

| 文件 | 作用 |
|---|---|
| `core.py` | 核心：链接解析、播客抓取、官方 feed 反查、RSS 渲染 |
| `build.py` | 单次生成（带本地缓存，可累积历史） |
| `publish.py` | 发布到 `docs/` 静态目录 |
| `refresh.py` | 批量刷新所有已登记播客（供 Actions 调用） |
| `server.py` | HTTP 接口，给快捷方式调用 |
| `shortcut/run.py` | 快捷方式逻辑的等价实现（测试用） |

## 免责声明

仅供个人自用。请尊重播客版权，不要传播付费或独占内容；请控制请求频率。
