# -*- coding: utf-8 -*-
"""22-area_budget.py —— 把"面积"这件事一次算清：四个面积 + 沉金收费 + 金预算表

踩过的坑：用户说"沉金超过 20 平方厘米了"，我量出来是 10.16 cm²（比例 19.62%）。
真相是有人把 **19.62%** 乘了 **外接方框** 99.18 cm²（菱形只占外框 52%，等于虚高一倍）。
所以这个脚本把分母、单位、收费口径全部写死，不给人算错的机会。

四个面积（不要混）：
  板面积      = 板框轮廓的 shoelace（菱形 5176 mm²；外接方框 9918 mm² —— 差 1.92 倍）
  开窗面积    = GTS ∪ GBS（阻焊开窗，比沉金略大）
  沉金面积    = (Cu ∧ 开窗)，**收费按这个**
  外接框面积  = 报价/排版用，不是"板面积"

用法:
  python 22-area_budget.py <gerber目录|zip> [--band 1.0] [--u 1U] [--json]
      --band  板边金带线宽 mm（默认 1.0，用来算"金带占多少金"）
      --u     金厚 1U" / 2U"
"""
import sys, os, re, json, math, zipfile, tempfile, subprocess
import numpy as np
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 嘉立创沉金收费（2025-12-26 公告，金价 1000 元/克基准）----
ENIG_BASE = {"1U": 140.0, "2U": 240.0}        # 元/㎡，沉金面积比例 ≤30%
ENIG_EXTRA = {"1U": 5.6, "2U": 11.2}          # 元/㎡，每超出 1% 的面积
ENIG_FREE_PCT = 30.0                          # 加收线

def enig_fee(board_mm2, gold_pct, u="1U"):
    """沉金费（元/片）。备注：加收是对整板每平方米，不是只对金的部分。"""
    m2 = board_mm2 / 1e6
    over = max(0.0, gold_pct - ENIG_FREE_PCT)
    unit = ENIG_BASE[u] + over * ENIG_EXTRA[u]
    return m2 * unit, unit, over

def perimeter(w, h, r=0.0):
    """圆角矩形周长（r 会被夹到 w/2、h/2）。"""
    r = max(0.0, min(r, w/2.0, h/2.0))
    return 2*(w - 2*r) + 2*(h - 2*r) + 2*math.pi*r

def rounded_rect_bbox(w, h, r=0.0, rot=0.0):
    r = max(0.0, min(r, w/2.0, h/2.0))
    th = math.radians(rot); c, s = math.cos(th), math.sin(th)
    xs, ys = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx*(w/2.0 - r), sy*(h/2.0 - r)
            xs.append(cx*c - cy*s); ys.append(cx*s + cy*c)
    return (max(xs)-min(xs) + 2*r, max(ys)-min(ys) + 2*r)

def board_area(w, h, r=0.0):
    r = max(0.0, min(r, w/2.0, h/2.0))
    return w*h - (4 - math.pi)*r*r

# ---- 读 Gerber ----
def find(d, *keys):
    for f in os.listdir(d):
        for k in keys:
            if k.lower() in f.lower(): return os.path.join(d, f)
    return None

def raster(path, sc, x0, y0, w, h):
    out = os.path.join(tempfile.gettempdir(), "ab_%s.png" % os.path.basename(path))
    env = dict(os.environ); env.update(GR_SC=str(sc), GR_X0="%.4f" % x0, GR_Y0="%.4f" % y0,
                                       GR_W="%.4f" % w, GR_H="%.4f" % h)
    subprocess.run([sys.executable, os.path.join(HERE, "04-gerber_raster.py"), path, out],
                   env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return np.array(Image.open(out).convert("L")) > 128

def main(src, band=1.0, u="1U", as_json=False):
    tmp = None
    if os.path.isfile(src) and src.lower().endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="ab"); zipfile.ZipFile(src).extractall(tmp); d = tmp
    else:
        d = src
    GKO = find(d, "BoardOutline", "Edge_Cuts")
    GTL = find(d, "TopLayer", "F_Cu"); GBL = find(d, "BottomLayer", "B_Cu")
    GTS = find(d, "TopSolderMask"); GBS = find(d, "BottomSolderMask")
    sys.path.insert(0, HERE)
    import _gpoly
    poly = _gpoly.polygon(GKO)
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    A = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i+1) % len(poly)]
        A += x1*y2 - x2*y1
    area = abs(A)/2.0
    bw, bh = max(xs)-min(xs), max(ys)-min(ys)
    per = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i+1) % len(poly)]
        per += math.hypot(x2-x1, y2-y1)
    sc = 20.0
    X0, Y0 = min(xs)-2, max(ys)+2
    W, H = (bw+4), (bh+4)
    def L(p): return raster(p, sc, X0, Y0, W, H) if p else None
    cu_t, cu_b, op_t, op_b = L(GTL), L(GBL), L(GTS), L(GBS)
    def AND(a, b): return (a & b) if (a is not None and b is not None) else np.zeros((1, 1), bool)
    gold = AND(cu_t, op_t) | AND(cu_b, op_b)
    gold_mm2 = gold.sum()/sc/sc
    open_px = (op_t.sum() if op_t is not None else 0) + (op_b.sum() if op_b is not None else 0)
    open_mm2 = float(open_px)/(sc*sc)          # 注意是 sc*sc；写成 sc/sc 会把 mm² 放大 400 倍
    pct = 100.0*gold_mm2/area
    fee, unit, over = enig_fee(area, pct, u)
    band_mm2 = band*per
    out = {
        "board_area_mm2": round(area, 2), "board_cm2": round(area/100, 2),
        "outline_bbox_mm": [round(bw, 3), round(bh, 3)],
        "order_bbox_mm": round(max(bw, bh) + 0.254, 3),
        "bbox_area_mm2": round((bw+0.254)*(bh+0.254), 2),
        "perimeter_mm": round(per, 2),
        "opening_mm2": round(open_mm2, 2), "gold_mm2": round(gold_mm2, 2),
        "gold_cm2": round(gold_mm2/100, 3), "gold_pct": round(pct, 2),
        "band_mm2": round(band_mm2, 2), "band_cm2": round(band_mm2/100, 3),
        "band_share_pct": round(100*band_mm2/gold_mm2, 1) if gold_mm2 else 0,
        "enig_unit_yuan_m2": unit, "enig_over_pct": round(over, 2),
        "enig_yuan_per_board": round(fee, 4),
        "weight_g": round(area*1.6/1000*1.85, 2),
    }
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1)); return out
    print("板面积（轮廓 shoelace）%.2f mm² = %.2f cm²   外接框 %.2f x %.2f（面积 %.0f mm²，是板面积的 %.2f 倍）"
          % (area, area/100, bw, bh, (bw)*(bh), (bw*bh)/area))
    print("送厂板框（+0.254 线宽） %.3f mm   周长 %.2f mm   重量 %.1f g" % (
        max(bw, bh)+0.254, per, area*1.6/1000*1.85))
    print("开窗面积 %.2f mm²   沉金面积 %.2f mm² = %.3f cm²   占比 %.2f%%" % (
        open_mm2, gold_mm2, gold_mm2/100, pct))
    print("沉金费：%.4f 元/片（%s，单价 %.1f 元/㎡%s）" % (
        fee, u, unit, "，超出 %.1f%% 加收" % over if over else "，未超 30% 不加收"))
    print("金带 %.2f mm 宽 × 周长 = %.2f mm² = 占沉金的 %.1f%%（改动它最省金）" % (
        band, band_mm2, 100*band_mm2/gold_mm2 if gold_mm2 else 0))
    print("提醒：比例的分母永远是**轮廓面积**；用外接框当分母会把菱形板的比例算成一半。")
    return out

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(2)
    band = 1.0; u = "1U"; js = "--json" in a
    if "--band" in a:
        i = a.index("--band"); band = float(a[i+1]); del a[i:i+2]
    if "--u" in a:
        i = a.index("--u"); u = a[i+1]; del a[i:i+2]
    if "--json" in a: a.remove("--json")
    main(a[0], band, u, js)
