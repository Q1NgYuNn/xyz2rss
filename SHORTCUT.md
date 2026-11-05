# 小宇宙播客 → RSS（iOS 快捷指令）

## 安装

1. 下载 [小宇宙转RSS.shortcut](minis://attachments/%E5%B0%8F%E5%AE%87%E5%AE%99%E8%BD%ACRSS.shortcut)
2. 在「文件」App 里点一下，选「共享」→「快捷指令」（或直接双击导入）
3. 若提示"无法验证"，去 设置 → 快捷指令 → 打开「允许不受信任的快捷指令」

## 用法

1. 在小宇宙里打开某个播客 → 分享 → **复制链接**
2. 运行快捷指令「小宇宙 → RSS」
3. 结果会显示 RSS 地址，**已自动复制到剪贴板**
4. 到 Apple 播客 / Overcast / Pocket Casts 里「通过 URL 添加节目」

## 它是怎么工作的

```
复制的小宇宙链接
   ↓ 正则取 24 位 pid
https://www.xiaoyuzhoufm.com/podcast/<pid>
   ↓ 下载页面、正则取播客标题
播客标题
   ↓ 查 Apple Podcasts
搜索结果 JSON
   ↓ 正则：同名 + 且 feedUrl 属于 feed.xyzfm.space
https://feed.xyzfm.space/<slug>   ← 小宇宙官方完整 RSS
```

全程**只读**，不需要登录，不含任何 token，不会上传任何数据。

## 为什么有些播客查不到

小宇宙只给**部分播客**（通常是已上架 Apple Podcasts 的那些）托管官方 feed
（`feed.xyzfm.space`）。其余播客：

- 小宇宙网页版只公开**最新 15 集**，没有任何分页接口
- 所以快捷指令会明确提示"没查到官方 RSS"，而不是给你一个错误链接

### 为什么不使用其他域名的 feed

实测发现 Apple Podcasts 上存在**同名但完全无关**的播客，例如：

| 播客 | Apple 上的同名结果 | 问题 |
|---|---|---|
| 问题青年 | `ximalaya.com/album/47129647.xml` | 喜马拉雅上的另一个节目，153 集 vs 147 集 |
| 福说聊天会 | `ximalaya.com/album/76735246.xml` | 同上 |
| 故事FM | `feeds.storyfm.cn/storyfm.xml` | 自建站，非小宇宙托管 |

因此快捷指令**只接受 `feed.xyzfm.space` 域名**，宁可提示失败，也不给错链接。

## 已转换好的订阅地址

见 https://q1ngyunn.github.io/xyz2rss/ ，目前包含：

- 得体广播站 · 57 集（完整）
- 重重电波 · 15 集
- 福说聊天会 · 15 集

新增播客可在本机运行：

```bash
export GITHUB_PAT=<token>
python3 add.py "<小宇宙链接>"
```

## 文件

| 文件 | 说明 |
|---|---|
| `make_shortcut.py` | 生成快捷指令的脚本（改参数后重跑即可） |
| `dist/小宇宙转RSS.shortcut` | 生成的快捷指令文件 |
| `shortcut/simulate.py` | 用 Python 模拟快捷指令逻辑，便于验证 |
| `core.py` / `add.py` / `refresh.py` | 服务端生成与批量发布（可选） |
