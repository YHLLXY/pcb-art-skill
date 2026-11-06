# -*- coding: utf-8 -*-
"""18-filter_assets.py —— 把 17 抓来的一堆图粗筛成一张图墙

  python 18-filter_assets.py assets/candidates [--target-mm 40] [--min-px 800]

对每张图判四件事（都是"能不能上板"，不是"好不好看"）：
  1. 够不够大：源图 < 800 px 时，描到 40 mm 宽会糊；
  2. 背景干不干净：四个角都不是白/透明 → 有明显的底色或照片背景，剔；
  3. 墨量：二值化后墨占比 <3%（太空）或 >55%（上板糊成一片），剔；
  4. 最细笔画：按目标宽度换算成 mm，<0.15 mm 就低于工艺下限（丝印 0.15 / 铜 0.13）。

输出：直接改写 <dir>/index.md 成一张图墙（PASS/REJECT + 理由 + 评分），
      并生成 picks.md 模板，等用户在墙里挑。

**自动评分只能筛掉明显不能用的，不能替你决定好不好看。**
"""
import argparse, os, sys
import numpy as np
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def analyze(p, target_mm):
    im = Image.open(p)
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im2 = im.convert("RGBA")
    a = np.asarray(im2)
    al = a[:, :, 3]
    rgb = a[:, :, :3].astype(int)
    H, W = al.shape
    opaque = al > 128
    notes, bad, score = [], [], 50

    if W < 800 and H < 800:
        bad.append("小于 800 px（%d×%d）" % (W, H)); score -= 25
    else:
        score += 5

    # 背景：两版都看——透明底最好；不透明的话四角要接近白
    corners = np.concatenate([rgb[:20, :20].reshape(-1, 3), rgb[:20, -20:].reshape(-1, 3),
                              rgb[-20:, :20].reshape(-1, 3), rgb[-20:, -20:].reshape(-1, 3)])
    corner_opaque = (al[:20, :20] > 128).mean()
    if has_alpha and opaque.mean() < 0.95:
        notes.append("透明底（%.0f%% 不透明）" % (100 * opaque.mean())); score += 10
    else:
        lum = corners.mean()
        if lum < 200:
            bad.append("四角发暗（亮度 %.0f）→ 有色背景/照片" % lum); score -= 25
        else:
            notes.append("白底"); score += 5

    # 墨量 + 最细笔画（灰度 * 不透明 二值化）
    g = np.asarray(im.convert("L")).astype(float)
    if has_alpha:
        g[~opaque] = 255
    ink = g < 128
    frac = ink.mean()
    if frac < 0.03:
        bad.append("墨量过低 %.1f%%（空图/只剩淡线）" % (100 * frac)); score -= 20
    elif frac > 0.55:
        bad.append("墨量过高 %.0f%%（上板会糊）" % (100 * frac)); score -= 25
    else:
        notes.append("墨量 %.0f%%" % (100 * frac)); score += 10

    runs = []
    for row in ink:
        idx = np.nonzero(row)[0]
        if len(idx) == 0: continue
        cuts = np.nonzero(np.diff(idx) > 1)[0]
        st = np.concatenate(([0], cuts + 1)); en = np.concatenate((cuts, [len(idx) - 1]))
        runs.append(idx[en] - idx[st] + 1)
    mm_per_px = float(target_mm) / max(W, H)
    if runs:
        r5 = float(np.percentile(np.concatenate(runs), 5)) * mm_per_px
        if r5 < 0.15:
            bad.append("最细笔画 %.3f mm < 0.15（描出来是毛刺）" % r5); score -= 30
        else:
            notes.append("最细笔画 %.2f mm（%.0f px）" % (r5, r5 / mm_per_px)); score += 8
    else:
        bad.append("没有笔画"); score -= 30

    return {"file": os.path.basename(p), "w": W, "h": H, "ok": not bad,
            "score": max(0, min(100, score)), "notes": notes + bad}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default="assets/candidates")
    ap.add_argument("--target-mm", type=float, default=40.0, help="上板后的最大边长度")
    a = ap.parse_args()
    D = a.dir
    if not os.path.isdir(D):
        print("没有这个目录：", D); sys.exit(2)
    rows, skipped = [], 0
    for n in sorted(os.listdir(D)):
        if os.path.splitext(n)[1].lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            if n.lower().endswith(".svg"):
                rows.append({"file": n, "ok": True, "score": 60, "notes": ["SVG（矢量，需自己出预览）"], "w": 0, "h": 0})
            skipped += 1
            continue
        try:
            rows.append(analyze(os.path.join(D, n), a.target_mm))
        except Exception as e:
            rows.append({"file": n, "ok": False, "score": 0, "notes": ["读不出来：%s" % e], "w": 0, "h": 0})
    rows.sort(key=lambda r: (not r["ok"], -r["score"]))
    L = ["# 素材图墙（粗筛后，请你挑）", "",
         "目标宽度 %.0f mm；分数只表示「能不能上板」，不表示好不好看。" % a.target_mm, "",
         "| 缩略图 | 文件 | 评分 | 能不能用 | 说明 |", "|---|---|---|---|---|"]
    for r in rows:
        thumb = "![](%s)" % r["file"] if r["w"] else "（矢量）"
        L.append("| %s | %s | %d | %s | %s |" % (thumb, r["file"], r["score"],
                                                "✅ 可用" if r["ok"] else "❌ 剔", "；".join(r["notes"])))
    L += ["", "## 你挑哪几张", "",
          "| 文件 | 要哪一部分（整幅/头部/边框） | 放哪（正面主视觉/背面/边框） |", "|---|---|---|",
          "| | | |", "", "> 只说「这个不错」我没法描摹：**要说清楚取哪一块**。"]
    open(os.path.join(D, "index.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    ok = sum(1 for r in rows if r["ok"])
    print("图墙 -> %s/index.md    可用 %d / 共 %d" % (D, ok, len(rows)))
    for r in rows[:12]:
        print("  %-42s %3d  %s" % (r["file"], r["score"], "OK " if r["ok"] else "   "))

if __name__ == "__main__":
    main()
