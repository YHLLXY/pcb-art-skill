# -*- coding: utf-8 -*-
"""徽记解码：一张 PNG 进去，四个判断出来。

  python 00-decode_badge.py badge.png 30          # 目标直径 30 mm

输出：
  1. 是"线稿型"还是"圆盘型"（决定画法：描线 vs 实心盘+挖空）
  2. 外圆/内圆半径（mm，按目标直径换算）
  3. 各颜色面积 + 做成金之后的金面积估算
  4. 最小笔画（mm）——决定扫描步距和最小线宽
"""
import sys, math
import numpy as np
from PIL import Image

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

src = sys.argv[1]
D = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

im = Image.open(src).convert("RGBA")
a = np.asarray(im).astype(int)
r, g, b, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
H, W = al.shape
opaque = al > 128
ys, xs = np.nonzero(opaque)
cy, cx = (ys.min() + ys.max()) / 2.0, (xs.min() + xs.max()) / 2.0
Y, X = np.mgrid[0:H, 0:W]
R = np.hypot(X - cx, Y - cy)
RO = (xs.max() - xs.min()) / 2.0
sc = D / (2 * RO)                      # mm per px
mm2 = sc * sc

transparent = ~opaque

# ---- 主色：不看"蓝/橙"，直接对不透明像素做直方图聚类（不引第三方库） ----
rgb = a[:, :, :3].astype(np.float64)
op = rgb[opaque]
q = (op // 32).astype(np.int32)                    # 每通道 5 bit
key = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
uniq, counts = np.unique(key, return_counts=True)
order = np.argsort(counts)[::-1]
centers = []
for k in order[:16]:
    if counts[k] < 0.02 * len(key): break
    c = op[key == uniq[k]].mean(axis=0)
    if all(np.linalg.norm(c - x) >= 48 for x in centers):
        centers.append(c)
    if len(centers) == 3: break
if not centers:
    print("这张图没有不透明像素，没法解"); sys.exit(1)
centers = np.array(centers)

d = np.stack([np.linalg.norm(rgb - c, axis=2) for c in centers], axis=0)
lab = d.argmin(axis=0)
masks = [opaque & (lab == i) for i in range(len(centers))]
masks.sort(key=lambda m: -m.sum())
A_ = masks[0] if len(masks) > 0 else np.zeros_like(opaque)
B_ = masks[1] if len(masks) > 1 else np.zeros_like(opaque)
other = opaque & ~A_ & ~B_

def hexof(c): return "#%02X%02X%02X" % tuple(int(v) for v in c)
nameA = hexof(centers[0])
nameB = hexof(centers[1]) if len(centers) > 1 else "—"

def mm(v): return v * mm2

print("文件        ", src)
print("尺寸        %d x %d px，有效直径 %.1f px -> %.1f mm" % (W, H, 2 * RO, D))
print("像素换算    %.5f mm/px" % sc)
print()
print("透明        %6d px  %5.1f%%" % (transparent.sum(), 100.0 * transparent.sum() / (W * H)))
print("主色 A      %6d px  %5.1f%%   %s" % (A_.sum(), 100.0 * A_.sum() / (W * H), nameA))
print("主色 B      %6d px  %5.1f%%   %s" % (B_.sum(), 100.0 * B_.sum() / (W * H), nameB))
print("其它        %6d px  %5.1f%%" % (other.sum(), 100.0 * other.sum() / (W * H)))
print("主色阶数    %d（阈值聚类，不用 sklearn）" % len(centers))

# 环带：从圆心向外找最后一段"实色"（用主色 A 判）
blue = A_                                    # 兼容下面的变量名：A_ 就是"盘"的颜色
ann = np.zeros_like(blue)
if blue.any():
    ring_frac = blue[(R > 0.6 * RO) & (R < RO)].sum() / max(1, ((R > 0.6 * RO) & (R < RO)).sum())
    RI = RO * 0.62
    for rr in np.arange(0.2 * RO, 0.95 * RO, 1.0):
        vals = blue[(R > rr - 2) & (R < rr + 2)]
        if len(vals) and vals.mean() > 0.5:
            RI = rr; break
    else:
        RI = RO * 0.62
else:
    ring_frac, RI = 0.0, RO * 0.6

print("外圆半径    %.1f px / %.2f mm" % (RO, RO * sc))
print("内圆半径    %.1f px / %.2f mm" % (RI, RI * sc))
print("环带实色率  %.1f%%  (>=60%% 判为圆盘型，按主色 %s 算)" % (100.0 * ring_frac, nameA))

kind = "圆盘型（实心盘 + 镂空字）" if ring_frac >= 0.6 else "线稿型（本身就是线）"
print("判定        ", kind)
print()

print()

if ring_frac >= 0.6:
    band = math.pi * (RO ** 2 - RI ** 2) * mm2
    pct = 100.0 * band / (86 * 54)
    print("整块填实：环带一项 %.1f mm2，86x54 板上占 %.2f%%" % (band, pct))
    if pct < 12:
        verdict = "可以直接填实（加中心图形也还在 12–24% 区间内）"
    elif pct < 20:
        verdict = "可以填实，但徽记会吃掉大部分金预算（上限 24%）"
    else:
        verdict = "太大：缩小直径，或只保留环带的一部分"
    print("  -> " + verdict)
print()
if ring_frac >= 0.6:
    print("建议（圆盘型）：实心盘整块铜 + 字做【阻焊盖住的黑镂空】，字本身不用描。")
    print("  开窗只比铜大 0.05 mm（单边 0.025），否则镂空字最细处的阻焊桥会被吃掉。")
    print("  扫描线步距 0.0125 mm、源图先放大 3×、行合并容差 0.008 mm；圆沿偏差做到 <=0.02 mm。")
else:
    print("建议（线稿型）：整枚扫描线 0.06 mm；外圆/内圆用 [\"CIRCLE\"] 矢量，别用扫描线画圆。")
