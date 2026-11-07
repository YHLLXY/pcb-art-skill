# -*- coding: utf-8 -*-
"""15-weave.py —— 编织纹生成器：直接回放参考板的纹路表（不重新设计）

参考板：86.2x54.2 哑黑+沉金（Hello Kitty，嘉立创已量产，背面有 JLCJLCJLCJLC 水印）

    python 15-weave.py --extract <参考板 GTL>      # 从参考板重新提取纹路表
    python 15-weave.py                            # 用内置表生成，打印统计
    python 15-weave.py --out wv.json              # 导出矩形表
    python 15-weave.py --preview 80 -40 26 12 12 out.png

设计原则（2026-11-06 定）：
  1. 纹路表 = 参考板逐 2 mm 单元统计出来的朝向，**照抄**，不重新设计；
  2. 板边只沿条纹方向截断（limx/limy），**绝不为了补满而横着加一条**；
  3. 覆盖率不是目标，是结果。参考板 56%，抄对了自然落在 54–58%。
"""
import argparse, json, math, os, subprocess, sys, tempfile

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---- 参考板实测（2026-11-07 晚上用官方样板重测，400 px/mm）----
# 之前写 PITCH=0.195 / LINE_W=0.103，是早期 100 px/mm 光栅上读出来的，**偏细 13%**：
#   线宽 0.103 → 间隙 0.090 mm，低于嘉立创 1 oz 的 0.10 下限，铜被蚀刻吃掉，
#   整片织纹糊成一块实心铜 —— 李欣雨那块板（LiXinYu SAU）就是这么没印出来的。
# 官方样板逐块量：线宽 0.115（p25=p50，p75 0.117）、间隙 0.105、周期 0.2225（±0.0005）。
# 2026-11-07 二审：从样板 Gerber 的**矢量数据**里量（不用光栅，光栅会把宽度放大 ~0.003）：
#   条纹厚度 p50 = 0.1121（样板自己有两族：0.11204 和 0.11557），
#   条纹周期 p50 = 0.2223（横 0.2222 / 竖 0.2223，极差 0.0001），
#   于是间隙 = 0.2223 - 0.1121 = 0.1102。这三条就是"照抄"。
CELL   = 2.0        # 单元 2 mm（朝向每 2 mm 换一次，和样板一致）
PITCH  = 0.2223     # 条纹周期（样板矢量实测）
LINE_W = 0.1121     # 条纹线宽（样板矢量实测 p50）
GAP_MIN = 0.10      # 嘉立创 1 oz 最小间距；PITCH-LINE_W = 0.1102，余量 0.0102
RAD    = 2.2        # 板框圆角
CLIPX, CLIPY = 40.85, 24.85

# 4x4 单元 = 8x8 mm 一个周期，取自参考板（行 = y 向下，列 = x 向右）
PATTERN = ["VHHV",
           "HHVV",
           "HVVH",
           "VVHH"]

def orient(i, j):
    # PATTERN 的行序是「图像方向」（第 0 行在 +y 最高处），而 j 是从 y=0 向上数，
    # 所以取行号要翻转：(4 - j%4) % 4。写反了会得到一块「上下镜像」的织纹，
    # 单元吻合度只有 55%（实测），肉眼在 14 px/mm 下看不出来。
    return PATTERN[(4 - j % 4) % 4][i % 4]

def weave_rects(clipx=CLIPX, clipy=CLIPY, rad=RAD, cell=CELL,
                pitch=PITCH, w=LINE_W):
    def limx(y):
        ay = abs(y)
        if ay > clipy: return 0.0
        if ay <= clipy-rad: return clipx
        d = clipy-rad; return clipx-rad+math.sqrt(max(0.0, rad*rad-(ay-d)**2))
    def limy(x):
        ax = abs(x)
        if ax > clipx: return 0.0
        if ax <= clipx-rad: return clipy
        d = clipx-rad; return clipy-rad+math.sqrt(max(0.0, rad*rad-(ax-d)**2))
    out = []
    njy = int(math.ceil(clipy/cell))+2
    njx = int(math.ceil(clipx/cell))+2
    # 横条：按「行」找同朝向的连续段
    for j in range(-njy, njy+1):
        y0, y1 = j*cell, (j+1)*cell
        if y1 <= -clipy or y0 >= clipy: continue
        i = -njx
        while i < njx:
            if orient(i, j) != "H":
                i += 1; continue
            k = i
            while orient(k+1, j) == "H": k += 1
            bx0, bx1 = i*cell, (k+1)*cell
            yy = y0 + pitch*0.5
            while yy < y1 - 1e-9:
                L = limx(yy)
                a0, a1 = max(bx0, -L), min(bx1, L)
                if a1-a0 > 0.02:
                    out.append((a0, yy, a1-a0, w))
                yy += pitch
            i = k + 1
    # 竖条：按「列」找同朝向的连续段
    for i in range(-njx, njx+1):
        x0, x1 = i*cell, (i+1)*cell
        if x1 <= -clipx or x0 >= clipx: continue
        j = -njy
        while j < njy:
            if orient(i, j) != "V":
                j += 1; continue
            k = j
            while orient(i, k+1) == "V": k += 1
            by0, by1 = j*cell, (k+1)*cell
            xx = x0 + pitch*0.5
            while xx < x1 - 1e-9:
                L = limy(xx)
                a0, a1 = max(by0, -L), min(by1, L)
                if a1-a0 > 0.02 and -clipx < xx < clipx:
                    out.append((xx-w/2.0, (a0+a1)/2.0, w, a1-a0))
                xx += pitch
            j = k + 1
    return out

def preview(rects, sc, x0, y0, w, h, path):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (int(w*sc), int(h*sc)), (0, 0, 0))
    d = ImageDraw.Draw(img)
    def P(x, y): return ((x-x0)*sc, (y0-y)*sc)
    for (l, yc, rw, rh) in rects:
        a = P(l, yc+rh/2.0); b = P(l+rw, yc-rh/2.0)
        if b[0] < 0 or a[0] > img.width or b[1] < 0 or a[1] > img.height: continue
        d.rectangle([a[0], a[1], b[0], b[1]], fill=(255, 255, 255))
    img.save(path); print("preview", path)

def extract(gerber, x0=-36.0, y0=12.0, W=40.0, H=24.0, sc=100.0):
    """从一块参考板 GTL 里统计 2 mm 单元朝向，返回 4x4 周期表。"""
    import numpy as np
    from PIL import Image
    RAST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "04-gerber_raster.py")
    out = os.path.join(tempfile.gettempdir(), "wv_extract.png")
    env = dict(os.environ); env["GR_SC"] = str(sc); env["GR_X0"] = str(x0)
    env["GR_Y0"] = str(y0); env["GR_W"] = str(W); env["GR_H"] = str(H)
    subprocess.run([sys.executable, RAST, gerber, out], check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    a = np.array(Image.open(out).convert("L")) > 128
    T = int(CELL*sc); ny, nx = a.shape[0]//T, a.shape[1]//T
    M = []
    for j in range(ny):
        row = ""
        for i in range(nx):
            t = a[j*T:(j+1)*T, i*T:(i+1)*T].astype(np.float32)
            m = max(1, T//8)
            t = t[m:T-m, m:T-m]
            vx = np.abs(np.diff(t, axis=1)).mean(); vy = np.abs(np.diff(t, axis=0)).mean()
            row += "." if t.mean() < 0.05 else ("H" if vy > vx else "V")
        M.append(row)
    for r in M: print(r)
    # 取 4x4（找最常见的一版）
    from collections import Counter
    c = Counter()
    for j in range(len(M)-3):
        for i in range(len(M[0])-3):
            blk = tuple(M[j+t][i:i+4] for t in range(4))
            c[blk] += 1
    best, n = c.most_common(1)[0]
    print("most common 4x4 block  x%d:" % n)
    for r in best: print("   ", r)
    return list(best)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract")
    ap.add_argument("--clip", nargs=2, type=float, default=[CLIPX, CLIPY])
    ap.add_argument("--r", type=float, default=RAD)
    ap.add_argument("--cell", type=float, default=CELL)
    ap.add_argument("--pitch", type=float, default=PITCH)
    ap.add_argument("--width", type=float, default=LINE_W)
    ap.add_argument("--out")
    ap.add_argument("--preview", nargs=6, metavar=("SC", "X0", "Y0", "W", "H", "OUT"))
    a = ap.parse_args()
    if a.extract:
        extract(a.extract); sys.exit(0)
    rs = weave_rects(a.clip[0], a.clip[1], a.r, a.cell, a.pitch, a.width)
    area = sum(w*h for (_, _, w, h) in rs)
    print("rects %d  copper %.0f mm2  (%.1f%% of 86.2x54.2)" % (len(rs), area, 100*area/(86.2*54.2)))
    print("pattern 'VHHV/HHVV/HVVH/VVHH'  cell %.1f  pitch %.3f  width %.3f  间隙 %.4f" % (
        a.cell, a.pitch, a.width, a.pitch - a.width))
    if a.pitch - a.width < GAP_MIN - 1e-9 or a.width < GAP_MIN - 1e-9:
        print("WARN 织纹过密：线宽 %.3f / 间隙 %.4f 低于 %.2f，制程做不出来（会糊成一块铜）" % (
            a.width, a.pitch - a.width, GAP_MIN))
    if a.out:
        json.dump(rs, open(a.out, "w")); print("wrote", a.out)
    if a.preview:
        sc, x0, y0, pw, ph, path = a.preview
        preview(rs, float(sc), float(x0), float(y0), float(pw), float(ph), path)
