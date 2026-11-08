# -*- coding: utf-8 -*-
"""交付前物理自检：尺寸 / 金面积 / 最小线宽 / 钻孔 / 圆环连续性。

用法:
  python 13-check.py <gerber.zip 或 解压目录> [--board 86x54]   # --board 省略时按量到的板框判
                      [--copper-min 0.13] [--silk-min 0.15] [--ring 15.0:0.5]

退出码 0 = 全绿；1 = 有 FAIL。
"""
import sys, os, re, zipfile, tempfile, subprocess, math
import numpy as np
from PIL import Image, ImageDraw

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ARGV = sys.argv[1:]
def opt(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        v = ARGV[i+1]; del ARGV[i:i+2]; return v
    return default

SRC       = ARGV[0] if ARGV else None
BOARD     = opt("--board", None)      # 不给就按量到的板框为准（换尺寸不用改命令）
GOLD_MAX  = float(opt("--gold-max", "24"))
GOLD_MIN  = float(opt("--gold-min", "8"))     # 低于此值"太黑显空"（参考板 22.2%）
SILK_MINP = float(opt("--silk-pct-min", "0.3"))  # 白丝印占比下限（参考板正面 1.49%）
BLACK_MIN = float(opt("--black-min", "55"))   # 哑黑占比下限（参考板实测 60.7%，原写 70 连参考板自己都不合格）
WEAVE     = "--weave" in ARGV                 # 织纹结构校验（默认关，装饰板开）
if WEAVE: ARGV.remove("--weave")
WV_MIN    = float(opt("--weave-min", "90"))   # 与参考板纹路表的吻合度下限（%）
WV_CELL   = float(opt("--weave-cell", "2.0")) # 单元 mm
WV_WIN    = [float(v) for v in opt("--weave-win", "-38,24,18,32").split(",")]
MD_OUT    = opt("--md", None)                 # 顺手出一张 Markdown 验收单
NAME      = opt("--name", os.path.basename(SRC or "board"))
CU_MIN    = float(opt("--copper-min", "0.13"))
SK_MIN    = float(opt("--silk-min", "0.15"))
RING      = opt("--ring", None)          # 形如 15.0:0.5  (半径mm:线宽mm)
CY        = float(opt("--ring-cy", "0")) # 圆环中心 y（板中心为原点）

if not SRC:
    print(__doc__); sys.exit(2)

tmp = None
if os.path.isfile(SRC) and SRC.lower().endswith(".zip"):
    tmp = tempfile.mkdtemp(prefix="gw")
    with zipfile.ZipFile(SRC) as z: z.extractall(tmp)
    ROOT = tmp
else:
    ROOT = SRC

def find(*keys):
    for f in os.listdir(ROOT):
        for k in keys:
            if k.lower() in f.lower(): return os.path.join(ROOT, f)
    return None

LAYERS = {
  "GTL": find("TopLayer", ".GTL"), "GBL": find("BottomLayer", ".GBL"),
  "GTS": find("TopSolderMask", ".GTS"), "GBS": find("BottomSolderMask", ".GBS"),
  "GTO": find("TopSilkscreen", ".GTO"), "GBO": find("BottomSilkscreen", ".GBO"),
  "GKO": find("BoardOutline", ".GKO"),
}
DRL = find(".DRL")

HERE = os.path.dirname(os.path.abspath(__file__))
RAST = os.path.join(HERE, "04-gerber_raster.py")
def raster(path, sc):
    out = os.path.join(tempfile.gettempdir(), "chk_%s_%d.png" % (os.path.basename(path), sc))
    env = dict(os.environ); env["GR_SC"] = str(sc)
    subprocess.run([sys.executable, RAST, path, out], check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return np.array(Image.open(out).convert("L")) > 128

def Lwin(key, sc, x0, y0, w, h):
    p = LAYERS.get(key)
    if not p: return None
    out = os.path.join(tempfile.gettempdir(), "chkw_%s_%d.png" % (key, int(sc)))
    env = dict(os.environ); env["GR_SC"] = str(sc)
    env["GR_X0"] = "%.4f" % x0; env["GR_Y0"] = "%.4f" % y0
    env["GR_W"] = "%.4f" % w; env["GR_H"] = "%.4f" % h
    subprocess.run([sys.executable, RAST, p, out], check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return np.array(Image.open(out).convert("L")) > 128

def L(key, sc=20):
    p = LAYERS[key]
    if not p: return None
    return raster(p, sc)

rows = []
def rec(name, value, ok, note="", warn=None):
    """ok 为 False 记 FAIL；warn 为 True 记 WARN（只提示，不影响退出码）"""
    v = "PASS" if ok else ("WARN" if warn else "FAIL")
    rows.append((name, value, v, note))

# ---------- 板框（先定位，再按板框开窗；不再假设板子居中） ----------
_g0 = Lwin("GKO", 10, -100, 100, 200, 200)
_ys, _xs = np.nonzero(_g0)
BX0 = -100 + _xs.min()/10.0; BX1 = -100 + _xs.max()/10.0
BY1 = 100 - _ys.min()/10.0;  BY0 = 100 - _ys.max()/10.0
CXX, CYY = (BX0+BX1)/2.0, (BY0+BY1)/2.0
WIN = (BX0-2.0, BY1+2.0, (BX1-BX0)+4.0, (BY1-BY0)+4.0)
_L = L
def L(key, sc=20):
    return Lwin(key, sc, *WIN)
gko = L("GKO")
ys, xs = np.nonzero(gko)
SC = 20.0; X0, Y0 = WIN[0], WIN[1]
w_mm = (xs.max() - xs.min()) / SC; h_mm = (ys.max() - ys.min()) / SC
sys.path.insert(0, HERE)
import _gpoly
_poly = _gpoly.polygon(LAYERS["GKO"])
_sx = 0.0
for i in range(len(_poly)):
    x1, y1 = _poly[i]; x2, y2 = _poly[(i+1) % len(_poly)]
    _sx += x1*y2 - x2*y1
AREA_MM2 = abs(_sx)/2.0
_box = Image.new("L", (gko.shape[1], gko.shape[0]), 0)
if len(_poly) >= 3:
    ImageDraw.Draw(_box).polygon([((x-WIN[0])*SC, (WIN[1]-y)*SC) for (x, y) in _poly], fill=255)
area = np.asarray(_box) > 0
_a2 = area.sum()/SC/SC
if AREA_MM2 > 0 and abs(_a2 - AREA_MM2) > 0.05*AREA_MM2:
    print("WARN 轮廓面积两种算法不一致：shoelace %.1f / 光栅 %.1f mm2" % (AREA_MM2, _a2))

if BOARD:
    want_w, want_h = [float(v) for v in BOARD.lower().split("x")]
    rec("板尺寸 mm", "%.2f x %.2f  %.0f mm2" % (w_mm, h_mm, AREA_MM2),
        abs(w_mm - want_w) <= 0.35 and abs(h_mm - want_h) <= 0.35,
        "期望 %.1f x %.1f（面积按轮廓算，不是外接框）" % (want_w, want_h))
else:
    rec("板尺寸 mm", "%.2f x %.2f  %.0f mm2" % (w_mm, h_mm, AREA_MM2), True,
        "没给 --board，以量到的板框为准（板框线宽会让它比名义尺寸大 0.2–0.3）；面积按轮廓算，不是外接框")

# ---------- 金面积 ----------
gtl, gbl = L("GTL"), L("GBL")
gts, gbs = L("GTS"), L("GBS")

def _and(x, y):
    """缺层时返回全 0，而不是让 None & None 崩掉——报 FAIL 比抛异常有用。"""
    return np.zeros_like(area) if (x is None or y is None) else (x & y)

gold_t = _and(gtl, gts); gold_b = _and(gbl, gbs)
gold = gold_t | gold_b
_missing = [k for k, v in (("GTL", gtl), ("GBL", gbl), ("GTS", gts), ("GBS", gbs)) if v is None]
if _missing:
    rec("层缺失", ",".join(_missing), False, "缺铜层/开窗层，金面积只能算成 0；先确认导出层齐不齐")
ratio = 100.0 * gold.sum() / area.sum()
rec("沉金面积", "%.2f mm2 = %.2f%%" % (gold.sum()/SC/SC, ratio),
    GOLD_MIN <= ratio <= GOLD_MAX,
    "参考板 22.2%%；**口径=Gerber 全图 20 px/mm**（含压在板框外、会被铣掉的金带，约高 25%%）："
    "要板上真值用 22-area_budget.py --sc 40。区间 %.0f–%.0f%%；正 %.2f%% / 背 %.2f%%" % (
        GOLD_MIN, GOLD_MAX, 100.0*gold_t.sum()/area.sum(), 100.0*gold_b.sum()/area.sum()),
    warn=(ratio < GOLD_MIN))

# ---------- 最小线宽 ----------
def run_stats(mask):
    """横向游程长度分布（px）。返回 (min, p5)。
    45° 边上一行只切到 1-2 px 的碎片，所以判定看 p5 而不是 min。"""
    all_runs = []
    for row in mask:
        idx = np.nonzero(row)[0]
        if len(idx) == 0: continue
        cuts = np.nonzero(np.diff(idx) > 1)[0]
        starts = np.concatenate(([0], cuts + 1)); ends = np.concatenate((cuts, [len(idx)-1]))
        all_runs.append(idx[ends] - idx[starts] + 1)
    if not all_runs: return 0, 0
    a = np.concatenate(all_runs)
    return float(a.min()), float(np.percentile(a, 5))
SC2 = 50.0
_gtl2 = L("GTL", SC2)
if _gtl2 is None:
    rec("最小铜宽 mm", "缺 GTL", False, "没有顶层铜层，先确认导出的层齐不齐")
else:
    mn, p5 = run_stats(_gtl2)
    rec("最小铜宽 mm", "%.3f (p5 %.3f / min %.3f)" % (p5/SC2, p5/SC2, mn/SC2), p5/SC2 >= CU_MIN - 0.02, "工艺下限 %.3f，按 p5 判" % CU_MIN)
gto = L("GTO", SC2); gbo = L("GBO", SC2)
silk = np.zeros_like(gto) if gto is not None else None
if gto is not None: silk = gto.copy()
if gbo is not None: silk = (silk | gbo) if silk is not None else gbo
if silk is not None and silk.any():
    mn2, p52 = run_stats(silk)
    rec("最小丝印 mm", "%.3f (p5 %.3f)" % (p52/SC2, p52/SC2), p52/SC2 >= SK_MIN - 0.02, "工艺下限 %.3f，按 p5 判" % SK_MIN)

# ---------- 三色配比（白丝印 / 哑黑） ----------
gto2 = L("GTO"); gbo2 = L("GBO")
silk_t = (gto2 & area) if gto2 is not None else np.zeros_like(area)
silk_b = (gbo2 & area) if gbo2 is not None else np.zeros_like(area)
silk_all = silk_t | silk_b
sp = 100.0*silk_all.sum()/area.sum()
rec("白丝印面积", "%.2f%%（正 %.2f / 背 %.2f）" % (sp, 100.0*silk_t.sum()/area.sum(), 100.0*silk_b.sum()/area.sum()),
    sp >= SILK_MINP, "参考板正 1.49%% / 背 23.27%%；下限 %.1f%%" % SILK_MINP, warn=True)
bp = 100.0*(area & ~gold & ~silk_all).sum()/area.sum()
rec("哑黑占比", "%.2f%%" % bp, bp >= BLACK_MIN, "参考板 60.70%%；下限 %.0f%%（整板铺金才会破这个数）" % BLACK_MIN, warn=True)

# ---------- 织纹结构（和参考板纹路表逐单元比对） ----------
# 参考板 86.2x54.2 哑黑+沉金 的 2 mm 单元朝向表（8x8 mm 一个周期）
WEAVE_REF = ["VHHV", "HHVV", "HVVH", "VVHH"]
if WEAVE:
    sc, (wx, wy, ww, wh) = 100.0, WV_WIN
    cu = Lwin("GTL", sc, wx, wy, ww, wh)
    _side = "正面"
    if cu is not None and cu.mean() < 0.10:      # 织纹可能只做了背面
        _b = Lwin("GBL", sc, wx, wy, ww, wh)
        if _b is not None and _b.mean() > cu.mean():
            cu, _side = _b, "背面"
    T = int(WV_CELL*sc)
    njy, nxi = cu.shape[0]//T, cu.shape[1]//T
    got = []
    for j in range(njy):
        row = ""
        for i in range(nxi):
            t = cu[j*T:(j+1)*T, i*T:(i+1)*T].astype(np.float32)
            m = max(1, T//8)
            t = t[m:T-m, m:T-m]
            if t.mean() < 0.05:
                row += "?"; continue
            vx = np.abs(np.diff(t, axis=1)).mean(); vy = np.abs(np.diff(t, axis=0)).mean()
            row += "H" if vy > vx else "V"
        got.append(row)
    # 量的是背面时，表要左右翻：layer 2 的几何是镜像的，直接比会只有 50%
    REF = [r[::-1] for r in WEAVE_REF] if _side == "背面" else WEAVE_REF
    best, bestd = -1, None
    for dj in range(4):
        for di in range(4):
            ok = sum(1 for j in range(njy) for i in range(nxi)
                     if got[j][i] == REF[(j+dj) % 4][(i+di) % 4])
            if ok > best: best, bestd = ok, (di, dj)
    tot = njy*nxi
    pct = 100.0*best/tot
    cov = 100.0*cu.mean()
    if cov < 10.0:
        # 窗口里几乎没铜：多半是"织纹不在这块区域"（只在背面、或窗口位置不对），
        # 这时候 3.5% 的吻合度是假 FAIL。先把窗口问题报出来（李欣雨/重邮两块板踩过）。
        rec("织纹吻合度", "窗口里只有 %.1f%% 铜，无法判" % cov, True,
            "用 --weave-win x0,y0,w,h 指到有织纹的地方（默认 %s）" % ",".join("%g" % v for v in WV_WIN), warn=True)
    else:
        rec("织纹吻合度", "%.1f%%（%s，相位 %s，%dx%d 单元）" % (pct, _side, bestd, nxi, njy),
            pct >= WV_MIN, "参考板纹路表 %s%s；下限 %.0f%%" % (
                "/".join(REF), "（背面已左右翻）" if _side == "背面" else "", WV_MIN))
    rows.append(("织纹覆盖率", "%.1f%%" % cov, "INFO", "参考板 56%，只作参考不判定"))
    # 工艺下限：线宽和间隙都必须 >= 0.10 mm。
    # 李欣雨那块板写的是 0.103/0.195（间隙 0.092），比样板细 13%，蚀刻直接吃掉 → 织纹没印出来。
    # **必须走矢量**：0.1 mm 级的细条在 100 px/mm 光栅上会被边缘糊掉 ±0.003，
    # 而这 0.003 正好决定做不做得出（0.092 与 0.100 之差就是"没有织纹"与"有织纹"）。
    try:
        _regs = _gpoly.regions(LAYERS["GBL" if _side == "背面" else "GTL"])
    except Exception:
        _regs = []
    _w, _p = [], []
    for _q in _regs:
        _xs = [q[0] for q in _q]; _ys = [q[1] for q in _q]
        _bx0, _bx1, _by0, _by1 = min(_xs), max(_xs), min(_ys), max(_ys)
        _cx, _cy = (_bx0 + _bx1) / 2.0, (_by0 + _by1) / 2.0
        if not (wx <= _cx <= wx + ww and wy - wh <= _cy <= wy):
            continue
        _bw, _bh = _bx1 - _bx0, _by1 - _by0
        if _bh < 0.30 and _bw > 0.8:
            _w.append(_bh); _p.append(_by0)
        elif _bw < 0.30 and _bh > 0.8:
            _w.append(_bw); _p.append(_bx0)
    if len(_w) >= 10:
        _ths = float(np.median(_w))
        _ps = np.array(sorted(set(round(v, 6) for v in _p)))
        _dd = np.diff(_ps); _dd = _dd[(_dd > 0.15) & (_dd < 0.30)]
        _pit = float(np.median(_dd)) if len(_dd) else 0.0
        _gap = _pit - _ths
        rec("织纹线宽/间隙", "%.4f / %.4f mm（矢量，周期 %.4f）" % (_ths, _gap, _pit),
            _ths >= 0.100 and _gap >= 0.100,
            "下限都是 0.100；官方样板 0.1121 / 0.1103（周期 0.2223）")

# ---------- 钻孔 ----------
if DRL:
    txt = open(DRL, encoding="utf-8", errors="ignore").read()
    tools_ = re.findall(r"T\d+C([\d.]+)", txt)
    hits = len(re.findall(r"^X[-\d.]+Y[-\d.]+$", txt, re.M))
    rec("钻孔", "%d 处 / 孔径 %s" % (hits, ",".join("%.2f" % float(t) for t in sorted(set(tools_), key=float))), hits >= 1, "PTH")

# ---------- 圆环连续性 ----------
if RING:
    rr, ww = [float(v) for v in RING.split(":")]
    SC3 = 100.0
    cu = L("GTL", SC3); op = L("GTS", SC3)
    g = cu & op
    H, W = g.shape
    cx = int(round((CXX - X0) * SC3)); cy = int(round((Y0 - (CYY + CY)) * SC3))
    Y, X = np.mgrid[0:H, 0:W]
    R = np.hypot(X - cx, Y - cy) / SC3
    band = np.abs(R - rr) < ww / 2 * 1.05
    cov = g[band].mean()
    rec("圆环覆盖率", "%.3f" % cov, cov >= 0.95, "r=%.2f w=%.2f" % (rr, ww))

if MD_OUT:
    import time as _t
    def _fmt(v):
        return v.replace("|", "/")
    L = []
    L.append("# 验收单：%s" % NAME)
    L.append("")
    L.append("生成时间：%s　｜　Gerber：%s" % (_t.strftime("%Y-%m-%d %H:%M:%S"), os.path.basename(SRC)))
    L.append("")
    L.append("> 这张表由 `scripts/13-check.py --md` 生成，第一部分的数字**不可手改**；")
    L.append("> 第二部分是 P4.5 的 14 项，必须用户逐条点头；第三部分填结论。")
    L.append("")
    L.append("## 一、实测（脚本输出）")
    L.append("")
    L.append("| 项目 | 实测 | 判定 | 说明 |")
    L.append("|---|---|---|---|")
    for a, b, c, d in rows:
        L.append("| %s | %s | **%s** | %s |" % (a, _fmt(b), c, _fmt(d)))
    L.append("")
    L.append("## 二、3D 验收（P4.5，逐条打勾）")
    L.append("")
    L.append("先看图：`preview/*_front3d.png` / `*_back3d.png` / `*_badge60.png`。")
    L.append("")
    L.append("**C1 缺陷（6）**")
    for q in ["文字没压边框/图形/孔", "金色面积合适（对比参考板）", "织纹两面都看得见",
              "背面元素镜像正确", "挂绳孔位置合理", "没有远看还行近看糊的元素"]:
        L.append("- [ ] %s" % q)
    L.append("")
    L.append("**C2 内容与排布（5）**")
    for q in ["重心不偏（竖起来看）", "疏密不打架（哪块空、要不要填）",
              "该加的没缺（周年/院系/日期/人名/地点）", "该删的没留（重复信息、凑数装饰）",
              "材质分工对（金/白/黑的量与位置）"]:
        L.append("- [ ] %s" % q)
    L.append("")
    L.append("**C3 素材（3）**")
    for q in ["有没有想放但手上没有的图", "要不要我去网上找（找到先给你看再描摹）",
              "有没有必须手写的地方"]:
        L.append("- [ ] %s" % q)
    L.append("")
    L.append("## 三、结论")
    L.append("")
    L.append("- [ ] 用户点头（日期 / 原话）：")
    L.append("- [ ] 需要改的项（改什么、改多少）：")
    L.append("- [ ] 下单包已生成，MANIFEST 回验一致（`19-pack_order.py --verify`）：")
    L.append("")
    _d = os.path.dirname(os.path.abspath(MD_OUT))
    os.makedirs(_d, exist_ok=True)
    open(MD_OUT, "w", encoding="utf-8").write("\n".join(L))
    print("验收单 ->", MD_OUT)

print()
print("%-14s %-28s %-6s %s" % ("项目", "实测", "判定", "说明"))
print("-" * 78)
for a, b, c, d in rows:
    print("%-14s %-28s %-6s %s" % (a, b, c, d))
print("-" * 78)
bad = [r for r in rows if r[2] == "FAIL"]
warn = [r for r in rows if r[2] == "WARN"]
tail = ("%d 项 FAIL" % len(bad)) if bad else "全绿"
if warn and not bad: tail += "（%d 项配比提示）" % len(warn)
print("结论：", tail)
print("下单包：python scripts/19-pack_order.py <包目录> 写 MANIFEST.txt（sha256）；解压后加 --verify 回验")
sys.exit(0 if not bad else 1)