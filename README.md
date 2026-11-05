# 小宇宙 → RSS

把小宇宙播客转换成标准播客 RSS，可在 Apple 播客 / Overcast / Pocket Casts 等客户端订阅。

**订阅页：https://q1ngyunn.github.io/xyz2rss/**

## 用法

### 添加一个新播客

```bash
export GITHUB_PAT=<你的 token>
python3 add.py "<小宇宙播客链接>"
```

约 1 分钟后刷新订阅页即可看到新地址。

### 批量添加

```bash
python3 add.py "<链接1>" "<链接2>" "<链接3>"
```

### 刷新已有播客（拿最新集数）

```bash
python3 refresh.py
git add docs && git commit -m "refresh" && git push
```

## 数据来源与局限（必读）

小宇宙**网页版只公开每个播客最新的 15 集**，没有分页接口
（`/v1/episode/list` 是创作者后台接口，匿名访问返回 401）。
因此分两种情况：

| 情形 | 集数 | 说明 |
|---|---|---|
| 小宇宙为该播客托管了官方 feed（`feed.xyzfm.space`） | **全部** | 通过 Apple Podcasts 反查得到，内容完整 |
| 其他播客 | 最新 15 集 | 网页公开数据的上限 |

> 反查时会严格校验：只接受 `feed.xyzfm.space` 域名，或其他域名但 feed 内容里
> 含该播客 pid 的。避免同名节目串台（曾经误抓到喜马拉雅上的同名播客，已修复）。

生成的 RSS 会把音频地址从官方统计跳转链接改写成 `media.xyzcdn.net` 直链，
已实测支持 Range 请求，客户端可正常拖动进度条。

## 安全说明

`GITHUB_PAT` **只从环境变量读取**，不写入任何文件，也不进入网页。
之前尝试过「网页内保存 token 并直接调用 GitHub API」的方案，因风险过高已废弃
（公开页面等于把 token 挂门上）。

## 文件说明

| 文件 | 作用 |
|---|---|
| `core.py` | 链接解析、播客抓取、官方 feed 反查与校验、RSS 渲染 |
| `build.py` | 单次生成（带本地缓存） |
| `publish.py` | 发布到 `docs/` |
| `add.py` | **一键添加**：生成 + 提交 + 推送 |
| `refresh.py` | 批量刷新所有已登记播客 |
| `server.py` | 本地 HTTP 接口（可选） |
| `docs/` | GitHub Pages 根目录，即线上订阅页 |

## 已知限制

- GitHub Actions 自动刷新未启用：当前 token 没有 `workflow` 权限，
  且公开仓库 60 天无活动会自动停用定时任务。目前靠手动 `refresh.py`。
- 未上架 Apple Podcasts 的播客只能拿到最新 15 集。

## 免责声明

仅供个人使用。请尊重播客版权，不要传播付费或独占内容，控制请求频率。
