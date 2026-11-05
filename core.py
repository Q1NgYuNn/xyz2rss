#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小宇宙播客 -> RSS 核心引擎（零第三方依赖，Python 3.8+）。

对外 API
--------
resolve(url)                 -> pid
load_podcast(pid)            -> dict（网页最新一页 + 元数据）
find_official_feed(pod)      -> feed url or None（Apple Podcasts 反查）
fetch_official_feed(url)     -> dict(pod_info, episodes, source='official')
render_rss(pod, episodes)    -> xml str
"""
import json
import re
import html
import gzip
import io
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

SITE = "https://www.xiaoyuzhoufm.com"
PID_RE = re.compile(r"[0-9a-f]{24}")
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


class XyzError(Exception):
    pass


# ------------------------------------------------------------------ HTTP
def http_get(url, timeout=25, retries=2):
    last = None
    for _ in range(retries + 1):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xml,application/json,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace"), r.geturl(), dict(r.headers)
        except urllib.error.HTTPError as e:
            last = XyzError("HTTP %s" % e.code)
            if e.code in (404, 410):
                break
        except Exception as e:  # noqa
            last = XyzError("%s: %s" % (type(e).__name__, e))
        time.sleep(0.8)
    raise last or XyzError("请求失败")


def http_head(url, timeout=15):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return dict(r.headers)
    except Exception:  # noqa
        return {}


# ------------------------------------------------------------ 链接解析
def resolve(url):
    """把各种小宇宙链接解析成 pid。"""
    url = (url or "").strip().strip("<>")
    if not url:
        raise XyzError("链接为空")

    m = re.search(r"xiaoyuzhoufm\.com/podcast/([0-9a-f]{24})", url)
    if m:
        return m.group(1)

    m = re.search(r"xiaoyuzhoufm\.com/episode/([0-9a-f]{24})", url)
    if m:
        return podcast_of_episode(m.group(1))

    if PID_RE.fullmatch(url):
        return url

    if "xyzfm.link" in url:
        body, final, _ = http_get(url)
        m = re.search(r"xiaoyuzhoufm\.com/podcast/([0-9a-f]{24})", final + body)
        if m:
            return m.group(1)
        m = re.search(r"xiaoyuzhoufm\.com/episode/([0-9a-f]{24})", final + body)
        if m:
            return podcast_of_episode(m.group(1))
        raise XyzError("分享链接未指向播客")

    raise XyzError("认不出这个小宇宙链接")


def _next_data(body):
    m = NEXT_DATA_RE.search(body)
    if not m:
        return None, None
    raw = m.group(1)
    return json.loads(raw), None


def episode_detail(eid):
    body, _u, _h = http_get("%s/episode/%s" % (SITE, eid))
    data, _ = _next_data(body)
    if data:
        ep = data.get("props", {}).get("pageProps", {}).get("episode")
        if ep:
            return ep
    raise XyzError("读取单集失败：%s" % eid)


def podcast_of_episode(eid):
    pid = episode_detail(eid).get("pid")
    if not pid:
        raise XyzError("单集没有所属播客")
    return pid


# ------------------------------------------------------------- 播客数据
def load_podcast(pid):
    """读取播客页（网页只给最新 15 集，但元数据完整、请求最便宜）。"""
    body, final, _ = http_get("%s/podcast/%s" % (SITE, pid))
    data, _ = _next_data(body)
    if not data:
        raise XyzError("页面结构异常，可能被风控拦截")
    pod = data.get("props", {}).get("pageProps", {}).get("podcast")
    if not pod:
        raise XyzError("播客不存在或已下架：%s" % pid)
    pod["_source_url"] = "%s/podcast/%s" % (SITE, pid)
    return pod


def find_official_feed(pod, timeout=15):
    """用播客名 / 主播名到 Apple Podcasts 反查 feedUrl（只认完全同名或用 pid 佐证）。"""
    titles = []
    if pod.get("title"):
        titles.append(pod["title"])
    for p in (pod.get("podcasters") or [])[:3]:
        n = (p.get("nickname") or "").strip()
        if n and n not in titles:
            titles.append(n)

    want = (pod.get("title") or "").strip()
    for term in titles[:2]:
        url = ("https://itunes.apple.com/search?term=%s&entity=podcast&country=cn&limit=15"
               % urllib.parse.quote(term))
        try:
            body, _u, _h = http_get(url, timeout=timeout, retries=1)
            results = json.loads(body).get("results", [])
        except Exception:  # noqa
            continue
        exact = [r for r in results
                 if (r.get("collectionName") or "").strip() == want and r.get("feedUrl")]
        if len(exact) == 1:
            return exact[0]["feedUrl"]
        for r in exact:
            if "feed.xyzfm.space" in r["feedUrl"]:
                return r["feedUrl"]
        if exact:
            return exact[0]["feedUrl"]
    return None


# -------------------------------------------------------- 官方 feed 解析
def _txt(el, path, ns=True):
    node = el.find(path)
    return node.text if node is not None and node.text else ""


def fetch_official_feed(feed_url, cache_etag=None):
    """拉官方 feed 并转成内部统一结构。"""
    body, _u, headers = http_get(feed_url, timeout=35)
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(body.encode("utf-8"))
    except ET.ParseError as e:
        raise XyzError("feed 解析失败：%s" % e)
    ch = root.find("channel")
    if ch is None:
        raise XyzError("feed 缺少 channel")

    IT = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
    img_node = ch.find(IT + "image")
    image = img_node.get("href") if img_node is not None else (_txt(ch, "image/url"))
    pod = {
        "title": _txt(ch, "title"),
        "author": _txt(ch, IT + "author") or _txt(ch, "author"),
        "description": _txt(ch, "description"),
        "image": {"picUrl": image} if image else {},
        "link": _txt(ch, "link"),
        "language": _txt(ch, "language") or "zh-cn",
        "itunes_category": (_txt(ch, IT + "category") or ""),
    }

    eps = []
    for it in ch.findall("item"):
        enc = it.find("enclosure")
        enc_url = enc.get("url") if enc is not None else ""
        enc_len = enc.get("length") if enc is not None else ""
        enc_type = enc.get("type") if enc is not None else "audio/mpeg"
        m = re.search(r"media\.xyzcdn\.net/(.+?)(?:\?|$)", enc_url or "")
        media_key = urllib.parse.quote(m.group(1), safe="/") if m else ""
        if media_key:
            enc_url = "https://media.xyzcdn.net/" + media_key
        guid = _txt(it, "guid") or enc_url
        dur = _txt(it, IT + "duration")
        eps.append({
            "eid": guid,
            "guid": guid,
            "title": _txt(it, "title"),
            "description": _txt(it, "description") or "",
            "shownotes": "",
            "pubDate": _txt(it, "pubDate") or "",
            "pubDateRaw": _txt(it, "pubDate") or "",
            "duration": dur,
            "enclosure": {"url": enc_url, "length": enc_len, "type": enc_type},
            "media": {"size": int(enc_len) if str(enc_len).isdigit() else 0,
                      "mimeType": enc_type},
            "link": re.sub(r"\?.*$", "", _txt(it, "link")) or "",
            "payType": "FREE",
        })
    return pod, eps, {"etag": headers.get("ETag"), "last_modified": headers.get("Last-Modified")}


# ---------------------------------------------------------------- 渲染
def _cdata(s):
    s = "" if s is None else str(s)
    return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def parse_date(v):
    """接受 ISO8601 或 RFC822。"""
    v = (v or "").strip()
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:  # noqa
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S"):
        try:
            dt = datetime.strptime(v, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:  # noqa
            continue
    return None


def rfc822(v):
    dt = parse_date(v) if isinstance(v, str) else v
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def duration_seconds(v):
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip()
    if s.isdigit():
        return int(s)
    total = 0
    parts = s.split(":")
    try:
        for p in parts:
            total = total * 60 + int(float(p))
    except Exception:  # noqa
        return 0
    return total


MARKDOWN_IMG = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def episode_html(ep, podcast_title=""):
    notes = (ep.get("shownotes") or "").strip()
    if notes and "<" in notes:
        body = notes
    else:
        text = (ep.get("description") or "").strip()
        text = MARKDOWN_IMG.sub(r'<p><img src="\1"/></p>', text)
        body = "".join(
            p if p.startswith("<p>") else "<p>%s</p>" % html.escape(p)
            for p in (x.strip() for x in text.splitlines()) if p)
    if podcast_title:
        body += '<p style="color:#888">来源：%s · 小宇宙</p>' % html.escape(podcast_title)
    return body or "<p>（无节目简介）</p>"


def render_rss(pod, episodes, base_url=None, limit=0, include_paid=True,
               self_url=None):
    pid = pod.get("pid") or ""
    title = pod.get("title") or "小宇宙播客"
    img = (pod.get("image") or {}).get("picUrl") or ""
    link = pod.get("link") or pod.get("_source_url") or ("%s/podcast/%s" % (SITE, pid))
    desc = pod.get("description") or pod.get("brief") or ""

    eps = [e for e in episodes if include_paid or (e.get("payType") or "FREE") == "FREE"]
    eps = sorted(eps, key=lambda e: parse_date(e.get("pubDateRaw") or e.get("pubDate"))
                 or datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)
    if limit:
        eps = eps[:int(limit)]

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"'
           ' xmlns:content="http://purl.org/rss/1.0/modules/content/"'
           ' xmlns:atom="http://www.w3.org/2005/Atom">',
           '<channel>',
           '<title>%s</title>' % html.escape(title),
           '<link>%s</link>' % html.escape(link),
           '<description>%s</description>' % _cdata(desc),
           '<language>%s</language>' % html.escape(pod.get("language") or "zh-cn"),
           '<lastBuildDate>%s</lastBuildDate>'
           % rfc822(datetime.now(timezone.utc))]

    if self_url:
        out.append('<atom:link href="%s" rel="self" type="application/rss+xml"/>'
                   % html.escape(self_url))
    if img:
        out += ['<itunes:image href="%s"/>' % html.escape(img),
                '<image><url>%s</url><title>%s</title><link>%s</link></image>'
                % (html.escape(img), html.escape(title), html.escape(link))]
    out += ['<itunes:author>%s</itunes:author>' % html.escape(pod.get("author") or ""),
            '<itunes:explicit>false</itunes:explicit>',
            '<itunes:owner><itunes:name>%s</itunes:name></itunes:owner>'
            % html.escape(pod.get("author") or title)]
    if pid:
        out.append('<itunes:keywords>%s</itunes:keywords>' % html.escape(pid))

    for ep in eps:
        eid = ep.get("eid") or ep.get("guid") or ""
        enc = (ep.get("enclosure") or {}).get("url") or ""
        if not enc and ep.get("mediaKey"):
            enc = "https://media.xyzcdn.net/" + urllib.parse.quote(ep["mediaKey"], safe="/")
        media = ep.get("media") or {}
        size = int(media.get("size") or 0)
        mime = media.get("mimeType") or "audio/mpeg"
        dur = duration_seconds(ep.get("duration"))
        body = episode_html(ep, title)
        item = ["<item>",
                "<title>%s</title>" % html.escape(ep.get("title") or "未命名"),
                "<link>%s</link>" % html.escape(
                    ep.get("link") or ("%s/episode/%s" % (SITE, eid))),
                '<guid isPermaLink="false">%s</guid>' % html.escape(eid),
                "<pubDate>%s</pubDate>" % rfc822(ep.get("pubDateRaw") or ep.get("pubDate")),
                "<description>%s</description>" % _cdata(body),
                "<content:encoded>%s</content:encoded>" % _cdata(body)]
        if enc:
            item.append('<enclosure url="%s" length="%d" type="%s"/>'
                        % (html.escape(enc), size, html.escape(mime)))
        if dur:
            item.append("<itunes:duration>%d</itunes:duration>" % dur)
        item += ["<itunes:episodeType>full</itunes:episodeType>",
                 "<itunes:explicit>false</itunes:explicit>",
                 "</item>"]
        out.append("".join(item))

    out += ["</channel>", "</rss>"]
    return "\n".join(out)


def rss_valid(xml_text):
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except Exception as e:  # noqa
        return False, str(e)
    items = root.findall("./channel/item")
    return True, len(items)
