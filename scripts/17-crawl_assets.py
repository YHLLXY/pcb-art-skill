# -*- coding: utf-8 -*-
"""17-crawl_assets.py —— 按关键词采集素材，或者直接吃一个本地目录

两种模式：
  1) 联网（维基共享资源 API，只取 CC/PD 授权，逐条记来源与许可）：
       python 17-crawl_assets.py --keywords "mascot outline;victorian frame" --out assets/candidates --limit 8
  2) 本地（没网、或用户已经存好图）：
       python 17-crawl_assets.py --from-dir D:/pics --out assets/candidates

产出：
  <out>/*.png|svg|jpg   下载/复制的文件
  <out>/meta.json       每条：来源 URL、许可、作者、像素尺寸、sha256
  <out>/index.md        给人看的图墙（缩略图 + 来源 + 许可）

纪律（见 references/08）：
  - 机器只做采集，**审美交给人**；抓到的一张都不许直接上板；
  - 只采 CC/PD/校方公开标识；商业 IP（Hello Kitty 这类）只作工艺参考，不进板；
  - 记不清许可的，不许进 candidates，宁可手动放。
"""
import argparse, hashlib, json, os, shutil, sys, time, urllib.parse, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = "https://commons.wikimedia.org/w/api.php"
UA = "gift-pcb-skill/0.1 (decorative PCB asset collection; contact: repo owner)"
EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp"}

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]

def safe_name(s, ext):
    keep = "".join(c if c.isalnum() or c in "-_." else "_" for c in s)[:60]
    return keep + ext

def save_meta(out, rows):
    json.dump(rows, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    L = ["# 素材候选（crawl）", "",
         "| 缩略图 | 文件 | 来源 | 许可 | 作者 |",
         "|---|---|---|---|---|"]
    for r in rows:
        thumb = "![](%s)" % r["file"] if r["file"].endswith((".png", ".jpg", ".jpeg", ".webp")) else "（SVG）"
        L.append("| %s | %s | %s | %s | %s |" % (thumb, r["file"], r.get("source", ""),
                                                r.get("license", "?"), r.get("artist", "")))
    L += ["", "> 挑的时候只说「要哪一张、哪一部分（整幅 / 头部 / 边框）」，不要只说「这个不错」。"]
    open(os.path.join(out, "index.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

def from_dir(src, out, limit):
    os.makedirs(out, exist_ok=True)
    rows = []
    for root, _, files in os.walk(src):
        for n in sorted(files):
            if os.path.splitext(n)[1].lower() not in EXT: continue
            p = os.path.join(root, n)
            if os.path.getsize(p) < 4 * 1024:                     # 小于 4 KB 的基本是图标/图标式贴图
                print("  跳过过小文件（%d B）: %s" % (os.path.getsize(p), n))
                continue
            dst = os.path.join(out, safe_name(os.path.splitext(n)[0], os.path.splitext(n)[1].lower()))
            if os.path.abspath(p) != os.path.abspath(dst): shutil.copy2(p, dst)
            rows.append({"file": os.path.basename(dst), "source": "local:" + p,
                         "license": "用户自备（自行确认）", "artist": "", "sha": sha(dst)})
            if limit and len(rows) >= limit: break
        if limit and len(rows) >= limit: break
    save_meta(out, rows)
    print("本地模式：收了 %d 个文件 -> %s" % (len(rows), out))
    return rows

def commons(keyword, out, limit, dry):
    q = {"action": "query", "format": "json", "generator": "search",
         "gsrsearch": keyword, "gsrnamespace": "6", "gsrlimit": str(limit),
         "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": "1200"}
    url = API + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    js = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8"))
    pages = (js.get("query") or {}).get("pages") or {}
    rows = []
    for _, pg in list(pages.items())[:limit]:
        if ".pdf" in pg.get("title", "").lower():
            continue                      # 从 PDF 抽出来的页，基本不是素材
        info = (pg.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "?")
        if not any(k in lic.upper() for k in ("CC", "PUBLIC DOMAIN", "PD")):
            print("  跳过（许可 %r）: %s" % (lic, pg.get("title")))
            continue
        src_url = info.get("thumburl") or info.get("url")
        if not src_url: continue
        ext = os.path.splitext(urllib.parse.urlparse(src_url).path)[1].lower() or ".png"
        if ext not in EXT: ext = ".png"
        name = safe_name(os.path.splitext(pg.get("title", "img").replace("File:", ""))[0], ext)
        if dry:
            print("  [dry] %s <- %s (%s)" % (name, src_url, lic)); continue
        os.makedirs(out, exist_ok=True)
        dst = os.path.join(out, name)
        try:
            req2 = urllib.request.Request(src_url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req2, timeout=30).read()
            if len(data) > 6 * 1024 * 1024:
                print("  跳过（>6 MB）: %s" % name); continue
            open(dst, "wb").write(data)
        except Exception as e:
            print("  下载失败 %s: %s" % (name, e)); continue
        rows.append({"file": name, "source": src_url, "license": lic,
                     "artist": (meta.get("Artist") or {}).get("value", "")[:80],
                     "sha": sha(dst), "kw": keyword})
        print("  + %-50s %s" % (name, lic))
        time.sleep(1.0)                     # 别把人家站当 CDN
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", default="", help="分号分隔；走维基共享资源（只取 CC/PD）")
    ap.add_argument("--from-dir", default="", help="本地目录模式（没网时用这个）")
    ap.add_argument("--out", default="assets/candidates")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--svg", action="store_true", help="只找矢量图（给查询加 filetype:drawing）")
    a = ap.parse_args()
    if a.from_dir:
        rows = from_dir(a.from_dir, a.out, a.limit)
    elif a.keywords:
        rows = []
        for kw in [k.strip() for k in a.keywords.split(";") if k.strip()]:
            if a.svg and "filetype:" not in kw:
                kw = kw + " filetype:drawing"
            print("关键词：", kw)
            rows += commons(kw, a.out, a.limit, a.dry_run)
        if a.dry_run: return
        save_meta(a.out, rows)
        print("共 %d 个文件 -> %s" % (len(rows), a.out))
    else:
        print(__doc__); sys.exit(2)
    print("下一步：python 18-filter_assets.py %s" % a.out)

if __name__ == "__main__":
    main()
