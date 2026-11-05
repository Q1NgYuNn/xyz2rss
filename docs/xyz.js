// 小宇宙 → RSS 转换核心（浏览器端，供转换页与快捷方式使用）
// 依赖：小宇宙页面 CORS 开放，可直接 fetch 播客页 HTML 并解析 __NEXT_DATA__

const XYZ = (() => {
  const SITE = 'https://www.xiaoyuzhoufm.com';

  function pidFrom(text) {
    if (!text) return null;
    const m = String(text).match(/xiaoyuzhoufm\.com\/podcast\/([0-9a-f]{24})/);
    if (m) return m[1];
    const e = String(text).match(/xiaoyuzhoufm\.com\/episode\/([0-9a-f]{24})/);
    if (e) return { episode: e[1] };
    const bare = String(text).trim().match(/^[0-9a-f]{24}$/);
    return bare ? bare[0] : null;
  }

  async function fetchText(url) {
    const r = await fetch(url, { credentials: 'omit' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.text();
  }

  function parseNextData(html) {
    const m = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
    if (!m) throw new Error('页面结构异常');
    return JSON.parse(m[1]);
  }

  async function loadPodcast(pid) {
    const html = await fetchText(`${SITE}/podcast/${pid}`);
    const data = parseNextData(html);
    const pod = data?.props?.pageProps?.podcast;
    if (!pod) throw new Error('播客不存在或已下架');
    return pod;
  }

  async function findOfficialFeed(pod) {
    const want = (pod.title || '').trim();
    if (!want) return null;
    const url = 'https://itunes.apple.com/search?term=' +
      encodeURIComponent(want) + '&entity=podcast&country=cn&limit=15';
    try {
      const r = await fetch(url);
      const d = await r.json();
      const hit = (d.results || []).filter(
        x => (x.collectionName || '').trim() === want && x.feedUrl);
      return hit.length ? hit[0].feedUrl : null;
    } catch (e) {
      return null;
    }
  }

  function cdata(s) {
    return '<![CDATA[' + String(s ?? '').replace(/]]>/g, ']]]]><![CDATA[>') + ']]>';
  }

  function rfc822(v) {
    if (!v) return '';
    const d = new Date(v);
    if (isNaN(d)) return '';
    return d.toUTCString();
  }

  function secs(v) {
    if (v == null) return 0;
    if (typeof v === 'number') return Math.round(v);
    const s = String(v).trim();
    if (/^\d+$/.test(s)) return parseInt(s, 10);
    let t = 0;
    for (const p of s.split(':')) t = t * 60 + (parseInt(p, 10) || 0);
    return t;
  }

  function epHtml(ep, podcastTitle) {
    const notes = (ep.shownotes || '').trim();
    let body;
    if (notes && notes.includes('<')) {
      body = notes;
    } else {
      const text = (ep.description || '').trim();
      body = text.split(/\n+/).filter(Boolean)
        .map(p => `<p>${p.replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))}</p>`)
        .join('');
    }
    if (podcastTitle) {
      body += `<p style="color:#888">来源：${podcastTitle} · 小宇宙</p>`;
    }
    return body || '<p>（无节目简介）</p>';
  }

  function buildRss(pod, episodes, opts = {}) {
    const esc = s => String(s ?? '').replace(/[<>&"]/g,
      c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
    const title = pod.title || '小宇宙播客';
    const img = pod.image?.picUrl || pod.image?.smallPicUrl || '';
    const link = `${SITE}/podcast/${pod.pid}`;
    const desc = pod.description || pod.brief || '';

    let eps = (episodes || []).slice().sort(
      (a, b) => new Date(b.pubDate || 0) - new Date(a.pubDate || 0));
    if (opts.limit) eps = eps.slice(0, opts.limit);

    const L = [];
    L.push('<?xml version="1.0" encoding="UTF-8"?>');
    L.push('<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" ' +
      'xmlns:content="http://purl.org/rss/1.0/modules/content/">');
    L.push('<channel>');
    L.push(`<title>${esc(title)}</title>`);
    L.push(`<link>${esc(link)}</link>`);
    L.push(`<description>${cdata(desc)}</description>`);
    L.push('<language>zh-cn</language>');
    L.push(`<lastBuildDate>${new Date().toUTCString()}</lastBuildDate>`);
    if (img) {
      L.push(`<itunes:image href="${esc(img)}"/>`);
      L.push(`<image><url>${esc(img)}</url><title>${esc(title)}</title><link>${esc(link)}</link></image>`);
    }
    L.push(`<itunes:author>${esc(pod.author || '')}</itunes:author>`);
    L.push('<itunes:explicit>false</itunes:explicit>');

    for (const ep of eps) {
      const eid = ep.eid || '';
      const url = `${SITE}/episode/${eid}`;
      let enc = ep.enclosure?.url || '';
      if (!enc && ep.mediaKey) enc = 'https://media.xyzcdn.net/' + ep.mediaKey;
      const size = ep.media?.size || 0;
      const mime = ep.media?.mimeType || 'audio/mpeg';
      const dur = secs(ep.duration);
      const body = epHtml(ep, title);
      L.push('<item>');
      L.push(`<title>${esc(ep.title || '未命名')}</title>`);
      L.push(`<link>${esc(url)}</link>`);
      L.push(`<guid isPermaLink="false">${esc(eid)}</guid>`);
      L.push(`<pubDate>${rfc822(ep.pubDate)}</pubDate>`);
      L.push(`<description>${cdata(body)}</description>`);
      L.push(`<content:encoded>${cdata(body)}</content:encoded>`);
      if (enc) L.push(`<enclosure url="${esc(enc)}" length="${size}" type="${esc(mime)}"/>`);
      if (dur) L.push(`<itunes:duration>${dur}</itunes:duration>`);
      L.push('<itunes:episodeType>full</itunes:episodeType>');
      L.push('</item>');
    }
    L.push('</channel>');
    L.push('</rss>');
    return L.join('\n');
  }

  async function convert(link, opts = {}) {
    let pid = pidFrom(link);
    if (pid && typeof pid === 'object') {
      const eid = pid.episode;
      const html = await fetchText(`${SITE}/episode/${eid}`);
      const data = parseNextData(html);
      pid = data?.props?.pageProps?.episode?.pid;
    }
    if (!pid) throw new Error('认不出这个小宇宙链接');

    const pod = await loadPodcast(pid);
    let episodes = pod.episodes || [];
    let source = 'web';

    const feed = await findOfficialFeed(pod);
    if (feed) {
      try {
        const xmlText = await fetchText(feed);
        const doc = new DOMParser().parseFromString(xmlText, 'application/xml');
        const items = [...doc.querySelectorAll('channel > item')];
        if (items.length) {
          episodes = items.map(it => {
            const enc = it.querySelector('enclosure');
            let u = enc?.getAttribute('url') || '';
            const mk = u.match(/media\.xyzcdn\.net\/(.+?)(?:\?|$)/);
            if (mk) u = 'https://media.xyzcdn.net/' + mk[1];
            return {
              eid: it.querySelector('guid')?.textContent || u,
              title: it.querySelector('title')?.textContent || '',
              description: it.querySelector('description')?.textContent || '',
              pubDate: it.querySelector('pubDate')?.textContent || '',
              duration: it.getElementsByTagName('itunes:duration')[0]?.textContent || '',
              enclosure: { url: u },
              media: { size: parseInt(enc?.getAttribute('length') || '0', 10), mimeType: enc?.getAttribute('type') || 'audio/mp4' },
            };
          });
          source = 'official';
        }
      } catch (e) {
        // 官方 feed 失败则退回网页数据
      }
    }

    return { pod, episodes, source, xml: buildRss(pod, episodes, opts) };
  }

  return { convert, buildRss, pidFrom };
})();

if (typeof module !== 'undefined') module.exports = XYZ;
