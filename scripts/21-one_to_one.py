# -*- coding: utf-8 -*-
"""21-one_to_one.py —— 出一张真·1:1 的 A4 实尺页（两块板子做错过尺寸之后加的）

为什么要有这个：屏幕上的图没有尺寸感，"96 mm 转 45°"到底多大，只有打出来才知道。
这块板第一次就是因为没打过，做出来才发现比 CD 还大一圈。

做法：把 Gerber 按 600 dpi 光栅化（1 px = 1/600 in），直接铺在 210x297 mm 的页上，
A4 打 100% 就是 1:1。页面自带 100 mm 标尺和 1:1 的硬币/银行卡/电池，用来验证打印机没缩放。

用法:
  python 21-one_to_one.py <spec.json> <gerber目录> <out.pdf> [--tag v1] [--name 蒲玟君]
  # Gerber 目录 = 13-check 能吃的那个（解压后的 *_p72v1 那一层）

输出: <out.pdf>（两页：正面 / 背面）+ 两个 <out>_p1.png / _p2.png（屏幕预览，非 1:1）
"""
import os, sys, math, subprocess, tempfile, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
K = 0.0254
INK = (20, 20, 22); GREY = (110, 110, 115); RED = (200, 40, 40)
BLUE = (30, 80, 170); LIGHT = (170, 170, 175); GOOD = (30, 120, 60)
PW, PH = 210.0, 297.0                  # A4 mm
FONT = os.environ.get("GIFT_PCB_FONT_UI", r"C:\Windows\Fonts\msyh.ttc")

# ---------- 尺寸几何 ----------
def rounded_rect_bbox(w, h, r=0.0, rot=0.0):
    """圆角矩形转 rot 度之后的精确外接框（不是拿 w,h 直接转）。"""
    r = max(0.0, min(r, w/2.0, h/2.0))
    th = math.radians(rot); c, s = math.cos(th), math.sin(th)
    xs, ys = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx*(w/2.0 - r), sy*(h/2.0 - r)
            xs.append(cx*c - cy*s); ys.append(cx*s + cy*c)
    return (max(xs) - min(xs) + 2*r, max(ys) - min(ys) + 2*r)

def board_area(w, h, r=0.0, rot=0.0):
    r = max(0.0, min(r, w/2.0, h/2.0))
    return w*h - (4 - math.pi)*r*r

def mass_g(area_mm2, thick=1.6, rho=1.85):
    return area_mm2 * thick / 1000.0 * rho

# ---------- 排版小工具 ----------
class Page:
    def __init__(self, sc):
        self.sc = sc
        self.px = lambda v: v*sc
        self.im = Image.new("RGB", (int(round(PW*sc)), int(round(PH*sc))), (255, 255, 255))
        self.d = ImageDraw.Draw(self.im)
    def f(self, mm, bold=False):
        return ImageFont.truetype(FONT, int(round(mm*self.sc)))
    def txt(self, x, y, s, mm, bold=False, col=INK, anchor="lt"):
        self.d.text((self.px(x), self.px(y)), s, font=self.f(mm, bold), fill=col, anchor=anchor)
    def rect(self, x0, y0, x1, y1, col, w=0.25):
        self.d.rectangle([self.px(x0), self.px(y0), self.px(x1), self.px(y1)],
                         outline=col, width=max(1, int(round(self.px(w)))))
    def line(self, x0, y0, x1, y1, col, w=0.2):
        self.d.line([self.px(x0), self.px(y0), self.px(x1), self.px(y1)],
                    fill=col, width=max(1, int(round(self.px(w)))))
    def txt_rot(self, x, y, s, mm, bold=False, col=INK):
        f = self.f(mm, bold)
        w, h = self.d.textbbox((0, 0), s, font=f)[2:]
        tmp = Image.new("RGB", (int(w)+6, int(h)+6), (255, 255, 255))
        ImageDraw.Draw(tmp).text((3, 3), s, font=f, fill=col)
        tmp = tmp.rotate(90, expand=True)
        self.im.paste(tmp, (int(self.px(x)) - tmp.width, int(self.px(y)) - tmp.height//2))
    def dim_v(self, x, y0, y1, label):
        w = max(1, int(round(self.px(0.22))))
        self.line(x, y0, x, y1, RED, 0.22)
        for y, s in ((y0, 1), (y1, -1)):
            a = self.px(0.9)
            self.d.polygon([(self.px(x), self.px(y)), (self.px(x)-a*0.45, self.px(y)+s*a),
                            (self.px(x)+a*0.45, self.px(y)+s*a)], fill=RED)
        self.txt_rot(x-1.0, (y0+y1)/2, label, 3.0, True, RED)
    def dim_h(self, y, x0, x1, label):
        self.line(x0, y, x1, y, RED, 0.22)
        a = self.px(0.9)
        for x, s in ((x0, 1), (x1, -1)):
            self.d.polygon([(self.px(x), self.px(y)), (self.px(x)+s*a, self.px(y)-a*0.45),
                            (self.px(x)+s*a, self.px(y)+a*0.45)], fill=RED)
        self.txt((x0+x1)/2, y-1.0, label, 3.0, True, RED, "mb")
    def ruler(self, x0, y, length=100.0):
        self.line(x0, y, x0+length, y, INK, 0.2)
        for i in range(int(length)+1):
            h = 4.0 if i % 10 == 0 else (2.6 if i % 5 == 0 else 1.6)
            self.line(x0+i, y, x0+i, y+h, INK, 0.2)
            if i % 20 == 0:
                self.txt(x0+i, y+h+0.4, str(i), 2.6, False, INK, "mt")
        self.txt(x0+length+5, y+1.0, "mm", 2.6, False, INK, "lt")

# ---------- Gerber 光栅 + 合成 ----------
def _raster(gerber, out, sc, x0, y0, w, h, extra=None, npx=None):
    env = dict(os.environ)
    env.update(GR_SC="%.6f" % sc, GR_X0="%.6f" % x0, GR_Y0="%.6f" % y0,
               GR_W="%.6f" % w, GR_H="%.6f" % h)
    env.update(extra or {})
    subprocess.run([sys.executable, os.path.join(HERE, "04-gerber_raster.py"), gerber, out],
                   env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    a = np.array(Image.open(out).convert("L")) > 127
    # 光栅器按 int(BW*SC) 取整，和调用方的 round 可能差 1 px —— 补到同一尺寸，
    # 否则后面 inside & CU 直接 broadcast 报错（第一次就是这么挂的）
    if npx and a.shape != (npx, npx):
        b = np.zeros((npx, npx), bool)
        h, w = min(npx, a.shape[0]), min(npx, a.shape[1])
        b[:h, :w] = a[:h, :w]
        a = b
    return a

def find_layer(d, *keys):
    for f in os.listdir(d):
        for k in keys:
            if k.lower() in f.lower():
                return os.path.join(d, f)
    return None

def read_drl(path):
    holes, cur = [], None
    for ln in open(path, encoding="utf-8", errors="ignore"):
        ln = ln.strip()
        m = __import__("re").match(r"^T(\d+)C([\d.]+)$", ln)
        if m:
            cur = float(m.group(2)); continue
        m = __import__("re").match(r"^X(-?[\d.]+)Y(-?[\d.]+)$", ln)
        if m and cur:
            holes.append((float(m.group(1)), float(m.group(2)), cur))
    return holes

def compose(d, sc, bbox_w, bbox_h, margin=1.5):
    """返回 (正面RGB, 背面RGB, 每张图的 mm 边长)。sc = px/mm。"""
    GTL = find_layer(d, "TopLayer", "F_Cu"); GBL = find_layer(d, "BottomLayer", "B_Cu")
    GTS = find_layer(d, "TopSolderMask"); GBS = find_layer(d, "BottomSolderMask")
    GTO = find_layer(d, "TopSilkscreen"); GBO = find_layer(d, "BottomSilkscreen")
    GKO = find_layer(d, "BoardOutline", "Edge_Cuts")
    missing = [n for n, v in (("GTL", GTL), ("GBL", GBL), ("GTS", GTS), ("GBS", GBS), ("GKO", GKO)) if not v]
    if missing:
        raise SystemExit("Gerber 目录缺层：%s（%s）" % (",".join(missing), d))
    Wmm = bbox_w + 2*margin
    Wp = int(round(Wmm*sc))
    X0, Y0 = -Wp/2.0/sc, Wp/2.0/sc
    tmp = tempfile.mkdtemp(prefix="o2o")
    def R(p):
        if not p: return np.zeros((Wp, Wp), bool)
        return _raster(p, os.path.join(tmp, "r.png"), sc, X0, Y0, Wp/sc, Wp/sc, npx=Wp)
    # 板内区域：用 GKO 多边形填（不泛洪——47 px/mm 下 2300 万像素，纯 Python BFS 要跑几分钟）
    sys.path.insert(0, HERE)
    import _gpoly
    poly = _gpoly.polygon(GKO)
    bm = Image.new("L", (Wp, Wp), 0)
    ImageDraw.Draw(bm).polygon([((x - X0)*sc, (Y0 - y)*sc) for (x, y) in poly], fill=255)
    inside = np.array(bm) > 0
    def side(cu, mk, sk, mirror):
        CU, MK, SK = R(cu), R(mk), R(sk) if sk else np.zeros_like(CU)
        rgb = np.full((Wp, Wp, 3), 255, np.uint8)
        rgb[inside] = (26, 26, 28)
        rgb[inside & CU & ~MK] = (32, 31, 29)
        rgb[inside & CU & MK] = (206, 172, 110)
        rgb[inside & MK & ~CU] = (120, 105, 80)
        rgb[inside & SK] = (238, 238, 232)
        im = Image.fromarray(rgb); dr = ImageDraw.Draw(im)
        for (x, y, dia) in read_drl(find_layer(d, ".DRL")) if find_layer(d, ".DRL") else []:
            cx, cy = (x - X0)*sc, (Y0 - y)*sc; r = dia/2*sc
            dr.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 255, 255))
        if mirror: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        return im
    front = side(GTL, GTS, GTO, False)
    back = side(GBL, GBS, GBO, True)
    return front, back, Wp/sc

def build(spec_path, gerber_dir, out_pdf, tag="v1", who="", sc=600/25.4):
    spec = json.load(open(spec_path, encoding="utf-8"))
    b = spec.get("frame") or spec["board"]
    w, h = float(b["w"]), float(b["h"])
    r = float(b.get("r", 0)); rot = float(b.get("rot", 0) or 0)
    bw, bh = rounded_rect_bbox(w, h, r, rot)
    area = board_area(w, h, r, rot)
    # 1) 1200 dpi 渲染再降采样：织纹 0.11 mm 在 600 dpi 只有 2.6 px，直接渲会有摩尔纹
    hi = 2*sc
    f_hi, b_hi, img_mm = compose(gerber_dir, hi, bw, bh)
    npx = int(round(img_mm*sc))
    f_lo = f_hi.resize((npx, npx), Image.LANCZOS)
    b_lo = b_hi.resize((npx, npx), Image.LANCZOS)
    img_mm = npx/sc
    board_in = (img_mm - bw)/2.0

    def page(side_cn, im, note, extra=None):
        p = Page(sc)
        p.txt(PW/2, 9, "%s%s 1:1 实尺图" % (who + " · " if who else "", side_cn), 5.0, True, INK, "mt")
        p.rect(13, 17.5, PW-13, 24.5, RED, 0.4)
        p.txt(PW/2, 21, "打印设置：A4 · 缩放 100%「实际大小」· 不要勾选「适应页面 / 缩放以适合」",
              3.4, True, RED, "mm")
        p.txt(PW/2, 26.5, note, 3.1, False, GREY, "mt")
        x0 = (PW - img_mm)/2.0
        p.im.paste(im, (int(round(p.px(x0))), int(round(p.px(33.0 - board_in)))))
        bx0, by0 = x0 + board_in, 33.0
        p.dim_v(bx0-7.0, by0, by0+bh, "%.2f" % bh)
        p.dim_h(by0+bh+8.0, bx0, bx0+bw, "%.2f" % bw)
        p.txt(PW-12, by0+2, "板 %.0f × %.0f，转 %g°" % (w, h, rot), 3.0, False, GREY, "rt")
        p.txt(PW-12, by0+6.5, "外框 %.2f × %.2f" % (bw, bh), 3.0, False, GREY, "rt")
        p.txt(PW-12, by0+11, "厚 1.6 · 面积 %.1f cm² · 约 %.0f g" % (area/100, mass_g(area)),
              3.0, False, GREY, "rt")
        p.ruler(15, 158)
        p.txt(15, 167, "先把这段量一下：不是 100 mm，说明打印机缩放了，整页作废", 2.8, True, BLUE, "lt")
        if extra: extra(p)
        p.txt(PW/2, PH-6, "%s · %s · 两张都按 1:1 打印，叠起来就是真实大小" % (tag, side_cn),
              2.6, False, GREY, "mb")
        return p

    def refs(p):
        cy = 203.0
        p.d.ellipse([p.px(24-12.5), p.px(cy-12.5), p.px(24+12.5), p.px(cy+12.5)],
                    outline=GREY, width=max(1, int(p.px(0.3))))
        p.txt(24, cy+14, "1 元硬币 φ25.0", 2.9, False, GREY, "mt")
        p.rect(48, cy-27, 48+85.6, cy+27, GREY, 0.3)
        p.txt(48+42.8, cy, "银行卡 85.6 × 54.0", 3.0, False, GREY, "mm")
        p.rect(150, cy-25.2, 150+14.5, cy+25.2, GREY, 0.3)
        p.txt(157.2, cy, "5 号电池 φ14.5 × 50.5", 2.9, False, GREY, "mm")
        p.txt(15, 238, "板子最宽处 = A4 宽的 %.0f%%（%.1f / 210 mm）" % (100*bw/PW, bw),
              3.0, False, GREY, "lt")

    def table(p):
        y = 176.0
        cols = [15, 40, 64, 90, 110]
        hdr = ["换算", "边长 mm", "外框 mm", "面积 cm²", "重量 g"]
        p.d.rectangle([p.px(13), p.px(y-1.6), p.px(PW-13), p.px(y+6.4)], fill=(238, 238, 240))
        for c, hs in zip(cols, hdr):
            p.txt(c, y, hs, 2.9, True, INK, "lt")
        y += 8.0
        for k, lab in ((1.0, "现在"), (0.875, "0.875×"), (0.75, "0.75×"), (0.625, "0.625×")):
            ww, hh = w*k, h*k
            bbx, bby = rounded_rect_bbox(ww, hh, r, rot)
            ar = board_area(ww, hh, r, rot)
            for c, v in zip(cols, [lab, "%.0f" % ww, "%.2f" % bbx, "%.1f" % (ar/100), "%.1f" % mass_g(ar)]):
                p.txt(c, y, v, 2.9, v is lab, INK, "lt")
            y += 7.0
        p.txt(15, y+1.5, "缩尺寸时：图形/位置跟着缩；织纹线宽与周期、孔径、板厚、金带宽是绝对值，不缩。",
              2.8, False, GREY, "lt")
        p.txt(15, y+6.5, "外框 ≤ 100 mm 才落在嘉立创常规特价档。",
              2.8, False, GREY, "lt")

    p1 = page("正面", f_lo, "成品外观按铜/开窗/丝印三层合成，不是 3D 渲染", refs)
    p2 = page("背面", b_lo, "镜像是正常的：这是从背后看的效果", table)
    p1.im.save(out_pdf, resolution=sc*25.4, save_all=True, append_images=[p2.im])
    for i, pg in ((1, p1), (2, p2)):
        pg.im.resize((1200, int(1200*pg.im.height/pg.im.width)), Image.LANCZOS).save(
            os.path.splitext(out_pdf)[0] + "_p%d.png" % i)
    print("1:1 ->", out_pdf)
    print("  页面 %.2f × %.2f mm（应为 %.1f × %.1f）· 板 %.2f mm · %d px" % (
        p1.im.width/sc, p1.im.height/sc, PW, PH, bw, npx))
    print("  自检：图 %d px / %.0f dpi = %.2f mm，与板框 %.2f 之差 %.3f mm（含 %.1f mm 白边）" % (
        npx, sc*25.4, npx/sc, bw, abs(npx/sc - bw - 2*1.5), 1.5))
    return bw

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 3:
        print(__doc__); sys.exit(2)
    kw = {}
    for k in ("--tag", "--name"):
        if k in a:
            i = a.index(k); kw[k.strip("-")] = a[i+1]; del a[i:i+2]
    build(a[0], a[1], a[2], tag=kw.get("tag", "v1"), who=kw.get("name", ""))
