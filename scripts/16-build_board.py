# -*- coding: utf-8 -*-
"""16-build_board.py —— 按 spec 直接生成 .epcb2（装饰板流水线）

把 UESTC70 那一轮临时写的 gen3.py + build3.py 合并成一个参数化脚本：
徽记（圆盘型/线稿型）+ 汉字扫描线 + 拉丁文本对象 + 织纹（15-weave）+ 外框 + 挂绳孔
+ 手绘稿（arts：整张位图扫描线转金）+ 纸面点阵（dots：白丝印点）。

用法:
  python 16-build_board.py <spec.json> <模板工程目录> <输出 .epcb2>

spec 结构见 gen/uestc70.spec.json；board 尺寸只用来画板框，真正的板框来自模板工程。
孔用 "holes": [{x,y,d,pad}]，参考板那套是主孔 φ3.0 + 8×φ0.305 一圈（见 references/07）。
"""
import json, math, os, random, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

K = 0.0254
_M = ImageDraw.Draw(Image.new("L", (8, 8), 0))

# 字体：**仓库里不含任何字体文件**。名字只是"角色"，具体用哪个字体由你指定：
#   1) spec 里的 "fonts": {"xingkai": "D:/fonts/LXGWWenKai-Regular.ttf"}
#   2) 环境变量 GIFT_PCB_FONT_<角色大写>，例如 GIFT_PCB_FONT_XINGKAI
#   3) 下面这张 Windows 默认表（STXINGKA 是商业字体，只在你自己电脑上存在）
# 想开源一份能跑的配置，用 OFL 字体（霞鹜文楷 LXGWWenKai / 思源宋体 SourceHanSerif），
# 换完字宽会变，金板数字要重新量（见 references/02「字体」）。
FONTS = {
    # 中文手写/楷体（角色名 xingkai，不代表必须用华文行楷）
    "xingkai": os.environ.get("GIFT_PCB_FONT_XINGKAI", r"C:\Windows\Fonts\STXINGKA.TTF"),
    "times":   os.environ.get("GIFT_PCB_FONT_TIMES",   r"C:\Windows\Fonts\times.ttf"),
    "timesbd": os.environ.get("GIFT_PCB_FONT_TIMESBD", r"C:\Windows\Fonts\timesbd.ttf"),
    "consola": os.environ.get("GIFT_PCB_FONT_CONSOLA", r"C:\Windows\Fonts\consola.ttf"),
}

def font_of(name, spec=None):
    """把角色名解析成字体文件路径；找不到时给一句能照做的错。"""
    fp = (spec or {}).get("fonts", {}).get(name) or FONTS.get(name, name)
    if not os.path.exists(fp):
        raise SystemExit(
            "找不到字体 %r -> %s\n"
            "三种解法（选一）：\n"
            "  1) spec 里写 \"fonts\": {\"%s\": \"/path/to/font.ttf\"}\n"
            "  2) 设环境变量 GIFT_PCB_FONT_%s=/path/to/font.ttf\n"
            "  3) 装一个 OFL 字体（霞鹜文楷 / 思源宋体）并把路径填进上面两种之一\n"
            "仓库里不带字体文件：商业字体不能进开源仓库。" % (name, fp, name, name.upper()))
    return fp

def text_mask(s, fp, width_mm, sp=0.10):
    n = len(s)
    px = max(6, int(width_mm*40/(n*0.95+sp*(n-1))))
    for _ in range(6):
        f = ImageFont.truetype(fp, px)
        tot = sum(_M.textlength(c, font=f) for c in s) + px*sp*(n-1)
        if tot <= 0: break
        px = max(6, int(px*width_mm*40/tot))
    f = ImageFont.truetype(fp, px)
    wid = [_M.textlength(c, font=f) for c in s]; gap = px*sp
    tot = sum(wid) + gap*(n-1)
    im = Image.new("L", (int(tot)+40, px*2+40), 0); d = ImageDraw.Draw(im); x = 20
    for c, w in zip(s, wid):
        d.text((x, 20), c, font=f, fill=255); x += w+gap
    return im.crop(im.getbbox())

def scan_rows(a, ppm, cx, cy, step, tol=0.008, minw=0.15):
    H, W = a.shape; s = 1.0/ppm; TH = H*s
    rows = int(round(TH/step)); xl = cx - W*s/2.0; yt = cy + TH/2.0
    open_, done = {}, []
    for r in range(rows):
        py = int(((r+0.5)*step)/s)
        if py >= H: break
        y_top = yt - r*step
        idx = np.nonzero(a[py])[0]; seen = set()
        if len(idx):
            cuts = np.nonzero(np.diff(idx) > 1)[0]
            st = np.concatenate(([0], cuts+1)); en = np.concatenate((cuts, [len(idx)-1]))
            for s0, s1 in zip(idx[st], idx[en]):
                x0 = xl+s0*s; x1 = xl+(s1+1)*s
                if x1-x0 < minw: x1 = x0+minw
                w = x1-x0; key = round(x0, 2); o = open_.get(key)
                if o is not None and abs(o[2]-w) <= tol and abs(o[1]-step*o[3]-y_top) < 1e-9:
                    o[3] += 1; seen.add(key)
                else:
                    if o is not None: done.append(o); del open_[key]
                    open_[key] = [x0, y_top, w, 1]; seen.add(key)
        for kk in list(open_):
            if kk not in seen: done.append(open_[kk]); del open_[kk]
    done.extend(open_.values())
    return [(l, yt-h/2.0+step/8, w, h) for (l, yt, w, n) in done for h in [n*step+step/8]]

def art_mask(a, Wb, Hb, step):
    """位图 -> 板网格布尔图（原点在板中心，左上角 y 最大）。

    a = {"png", "w"(mm 宽), "cx", "cy", "thr"}；重采样到 step 网格后按亮度阈值取墨，
    所以扫描线采样点与像素中心严格对齐（不要直接拿原图分辨率去扫）。
    """
    im = Image.open(a["png"]).convert("L")
    wmm = float(a["w"])
    Wpx = max(8, int(round(wmm/step)))
    Hpx = max(8, int(round(im.height*wmm/im.width/step)))
    arr = np.asarray(im.resize((Wpx, Hpx), Image.LANCZOS)).astype(float)
    m = arr < float(a.get("thr", 150))
    if a.get("invert"): m = ~m
    full = np.zeros((Hb, Wb), bool)
    cx, cy = float(a.get("cx", 0.0)), float(a.get("cy", 0.0))
    j0 = int(round((cx - Wpx*step/2.0 + Wb*step/2.0)/step))
    i0 = int(round((Hb*step/2.0 - cy - Hpx*step/2.0)/step))
    js, je = max(0, j0), min(Wb, j0+Wpx)
    is_, ie = max(0, i0), min(Hb, i0+Hpx)
    if je > js and ie > is_:
        full[is_:ie, js:je] = m[is_-i0:ie-i0, js-j0:je-j0]
    return full

def dilate(m, px):
    """方形结构元膨胀（不引 scipy）。"""
    out = m.copy()
    for _ in range(int(px)):
        o2 = out.copy()
        o2[1:, :] |= out[:-1, :]; o2[:-1, :] |= out[1:, :]
        o2[:, 1:] |= out[:, :-1]; o2[:, :-1] |= out[:, 1:]
        out = o2
    return out

def badge_rects(spec, gap=0.05):
    """圆盘型：实心盘 + 字做黑镂空；线稿型：只留图形轮廓内的笔画。"""
    b = spec["badge"]; up = int(b.get("upsample", 3))
    im = Image.open(b["png"]).convert("RGBA")
    im = im.resize((im.width*up, im.height*up), Image.LANCZOS)
    a = np.asarray(im).astype(int)
    r_, g_, bb_, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
    H, W = al.shape
    cy0, cx0 = 510.5*up, 511.0*up
    Y, X = np.mgrid[0:H, 0:W]; R = np.hypot(X-cx0, Y-cy0)
    blue   = (al > 128) & (bb_ > 110) & (bb_ > r_+30)
    orange = (al > 128) & (r_ > 170) & (g_ > 70) & (g_ < 170) & (bb_ < 110)
    RO = float(b.get("r_out_px", 510.7))*up; RI = float(b.get("r_in_px", 318.0))*up
    ann = (R <= RO) & (R >= RI)
    knock = ann & ~blue & ~orange
    motif = (R <= RI) & (blue | orange)
    gold = (ann & ~knock | motif) if b.get("mode", "disc") == "disc" else (knock | motif)
    ppm = 2.0*RO/float(b["d"])
    rs = scan_rows(gold, ppm, float(b["cx"]), float(b["cy"]),
                   float(b.get("step", 0.0125)), minw=float(b.get("minw", 0.15)))
    return rs, gold.sum()/ppm**2

def main(spec_path, tpl_dir, out_pcb):
    spec = json.load(open(spec_path, encoding="utf-8"))
    # 相对路径按 spec 文件所在目录解析（允许 spec 与徽记图放一起，在任意 cwd 下跑）
    _base = os.path.dirname(os.path.abspath(spec_path))
    if spec.get("badge") and not os.path.isabs(spec["badge"].get("png", "")):
        spec["badge"]["png"] = os.path.join(_base, spec["badge"]["png"])
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import importlib.util
    wv_spec = importlib.util.spec_from_file_location(
        "weave", os.path.join(os.path.dirname(os.path.abspath(__file__)), "15-weave.py"))
    wv = importlib.util.module_from_spec(wv_spec); wv_spec.loader.exec_module(wv)

    groups = []          # [(layer, rects)]
    stats = {}
    if spec.get("weave"):
        c = spec["weave"]
        rs = wv.weave_rects(*c.get("clip", [40.85, 24.85]), c.get("r", 2.2))
        groups += [(1, rs), (2, [( -(l+w), y, w, h) for (l, y, w, h) in rs])]
        stats["weave"] = (len(rs), sum(w*h for _, _, w, h in rs))
    if spec.get("badge"):
        rs, area = badge_rects(spec)
        g = spec["badge"].get("mask_expand", 0.05)
        groups += [(1, rs), (5, [(l-g/2, y+g/2, w+g, h+g) for (l, y, w, h) in rs])]
        stats["badge"] = (len(rs), area)
    for t in spec.get("texts", []):
        m = text_mask(t["s"], font_of(t.get("font", "xingkai"), spec), t["width"], t.get("sp", 0.10))
        ppm = t.get("ppm", 40.0)
        rs = scan_rows(np.asarray(m) > 127, ppm, t["cx"], t["cy"],
                       t.get("step", 0.06), minw=t.get("minw", 0.14))
        if t.get("mirror"):
            rs = [(-(l+w), y, w, h) for (l, y, w, h) in rs]
        groups.append((t.get("layer", 1), rs))
        if t.get("mask_layer", 5) is not None:      # null = 纯丝印，不开窗
            g = t.get("mask_expand", 0.10)
            groups.append((t["mask_layer"], [(l-g/2, y+g/2, w+g, h+g) for (l, y, w, h) in rs]))
        stats[t["s"]] = (len(rs), sum(w*h for _, _, w, h in rs))

    # ---- 模板头 + 板框 ----
    src_pcb = os.path.join(tpl_dir, "pcb", "PCB1.epcb2")
    lines = [l for l in open(src_pcb, encoding="utf-8").read().split("\n") if l.strip()]
    KEEP = {"DOCHEAD","META","PRIMITIVE","LAYER","LAYER_PHYS","RULE","RULE_TEMPLATE",
            "CANVAS","ACTIVE_LAYER","PREFERENCE","SILK_OPTS"}
    head, out, tk = [], [], 0
    for l in lines:
        t_ = l.split('"type":"')[1].split('"')[0]
        m_ = re.search(r'"ticket":(\d+)', l)
        if m_: tk = max(tk, int(m_.group(1)))
        if t_ in KEEP: head.append(l)
        elif t_ == "POLY" and '"layerId":11' in l and not spec.get("board"):
            out.append(l)
    out = head + out
    uid = lambda: "%016x" % random.getrandbits(64)
    q = lambda v: round(v, 4)

    # ---- 手绘稿 / 点阵（都走同一张板网格；背面靠镜像掩膜，不靠 mirror:true）----
    rstep = float(spec.get("step", 0.06))
    if spec.get("arts") or spec.get("dots"):
        bw, bh = float(spec["board"]["w"]), float(spec["board"]["h"])
        Wb, Hb = int(round(bw/rstep)), int(round(bh/rstep))
        ink_all = np.zeros((Hb, Wb), bool)
        for a in spec.get("arts", []):
            m = art_mask(a, Wb, Hb, rstep)
            # 背面：整张掩膜左右翻（比翻 rect 更省事，且与点阵裁剪共用同一张图）
            if a.get("mirror"): m = m[:, ::-1]
            ink_all |= m
            rs = scan_rows(m, 1.0/rstep, 0.0, 0.0, rstep,
                           tol=float(a.get("tol", 0.008)), minw=float(a.get("minw", 0.15)))
            groups.append((int(a.get("layer", 2)), rs))
            ms = a.get("mask_layer", 6)
            if ms is not None:
                g = float(a.get("mask_expand", 0.05))
                groups.append((int(ms), [(l-g/2, y+g/2, w+g, h+g) for (l, y, w, h) in rs]))
            stats["art:" + os.path.basename(a["png"])] = (len(rs), sum(w*h for _, _, w, h in rs))
        d = spec.get("dots")
        if d:
            rr, pp = float(d["r"]), float(d["pitch"])
            mx = -bw/2.0 + (np.arange(Wb)+0.5)*rstep
            my =  bh/2.0 - (np.arange(Hb)+0.5)*rstep
            dm = np.zeros((Hb, Wb), bool)
            ink_d = dilate(ink_all, int(round(0.15/rstep)))        # 墨线上不印白点
            keep = float(d.get("keep", 0.75))                     # 被墨吃掉 >25% 的点直接不要
            for j in range(int(d.get("nx", 1))):
                for i in range(int(d.get("ny", 1))):
                    cxd = float(d["ox"]) + float(d["x0"]) + j*pp
                    cyd = float(d["oy"]) - (float(d["y0"]) + i*pp)
                    if d.get("mirror", True): cxd = -cxd
                    sel = np.abs(mx - cxd) <= rr + 2*rstep
                    se2 = np.abs(my - cyd) <= rr + 2*rstep
                    if not sel.any() or not se2.any(): continue
                    ri, ci = np.nonzero(se2)[0], np.nonzero(sel)[0]
                    sub = (((mx[ci][None, :]-cxd)**2 + (my[ri][:, None]-cyd)**2) <= rr*rr)
                    if (sub & ink_d[np.ix_(ri, ci)]).sum() > (1.0-keep)*sub.sum():
                        continue                                  # 剩个白月牙比没有更难看
                    dm[np.ix_(ri, ci)] |= sub
            dm &= ~ink_d
            for h_ in (spec.get("holes") or ([spec["hole"]] if spec.get("hole") else [])):
                pr = float(h_.get("pad") or h_["d"])/2.0 + rr + 0.25
                dm &= ((mx[None, :] - h_["x"])**2 + (my[:, None] - h_["y"])**2) > pr*pr
            rs = scan_rows(dm, 1.0/rstep, 0.0, 0.0, rstep, minw=0.15)
            groups.append((int(d.get("layer", 4)), rs))
            stats["dots"] = (len(rs), sum(w*h for _, _, w, h in rs))

    def poly(layer, path, width_mm):
        nonlocal tk; tk += 1
        o = {"partitionId":"","groupId":0,"netName":"","layerId":layer,"width":q(width_mm/K),
             "path":path,"locked":False,"zIndex":-1,"polyType":"NORMAL"}
        out.append('{"type":"POLY","ticket":%d,"id":"%s"}||%s|' % (tk, uid(), json.dumps(o, ensure_ascii=False, separators=(',',':'))))

    bd = spec.get("board")
    if bd:                                   # 板框按 spec 重画（模板那块是 86x54）
        # 板框线宽 10 mil（=0.254 mm）。写成 10 会被当成 10 mm，把 GKO 的 bbox 撑大 10 mm，
        # 于是 13-check 的分母全错（84x90 就是这么来的）。
        poly(11, ["R", q(-float(bd["w"])/2/K), q(float(bd["h"])/2/K), q(float(bd["w"])/K),
                  q(float(bd["h"])/K), 0, q(float(bd.get("r", 3.5))/K)], 10*K)

    for layer, rs in groups:
        for (l, y, w, h) in rs:
            tk += 1
            path = [["R", q(l/K), q((y+h/2.0)/K), q(w/K), q(h/K), 0, 0]]
            o = {"partitionId":"","groupId":0,"netName":"","layerId":layer,"width":0.2,
                 "fillStyle":"SOLID","path":path,"locked":False,"zIndex":-1,
                 "isBridgingCopper":False,"networkList":[],"refs":[None]}
            out.append('{"type":"FILL","ticket":%d,"id":"%s"}||%s|' % (tk, uid(), json.dumps(o, ensure_ascii=False, separators=(',',':'))))

    f = spec.get("frame")
    if f:
        for layer, wmm in ((1, f.get("cu", 0.40)), (5, f.get("mask", 0.50)),
                           (2, f.get("cu", 0.40)), (6, f.get("mask", 0.50))):
            poly(layer, ["R", q(-f["w"]/2/K), q(f["h"]/2/K), q(f["w"]/K), q(f["h"]/K),
                         0, q(f.get("r", 2.5)/K)], wmm)

    for s in spec.get("strings", []):
        tk += 1
        o = {"partitionId":"","groupId":0,"layerId":s["layer"],"x":s["x"],"y":s["y"],
             "text":s["text"],"fontFamily":"default","fontSize":s["size"],"strokeWidth":s.get("sw", 6.5),
             "bold":False,"italic":False,"origin":"LEFT_BOTTOM","angle":0,"reverse":False,
             "expansion":0,"mirror":False,"locked":False,"zIndex":3}
        out.append('{"type":"STRING","ticket":%d,"id":"%s"}||%s|' % (tk, uid(), json.dumps(o, ensure_ascii=False, separators=(',',':'))))

    # 孔：支持单孔(hole)或多孔(holes)；参考板是「主孔 φ3.0 + 8×φ0.305 一圈」
    holes = spec.get("holes") or ([spec["hole"]] if spec.get("hole") else [])
    for n, h in enumerate(holes):
        tk += 1
        pad_d = float(h.get("pad") or h["d"])
        o = {"partitionId":"","groupId":0,"netName":"","layerId":12,"num":str(n+1),
             "centerX":q(h["x"]/K),"centerY":q(h["y"]/K),"padAngle":0,
             "hole":{"holeType":"ROUND","width":q(h["d"]/K),"height":q(h["d"]/K),"cornerRadius":q(0.3/K)},
             "defaultPad":{"padType":"ELLIPSE","width":q(pad_d/K),"height":q(pad_d/K)},
             "specialPad":[],"padOffsetX":0,"padOffsetY":0,"relativeAngle":0,
             "plated":bool(h.get("plated", True)),
             "padType":"NORMAL","topSolderExpansion":None,"bottomSolderExpansion":None,
             "topPasteExpansion":None,"bottomPasteExpansion":None,"locked":False}
        out.append('{"type":"PAD","ticket":%d,"id":"%s"}||%s|' % (tk, uid(), json.dumps(o, ensure_ascii=False, separators=(',',':'))))

    _d = os.path.dirname(os.path.abspath(out_pcb))       # 允许 out/ 这种还不存在的目录
    os.makedirs(_d, exist_ok=True)
    open(out_pcb, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("wrote %s  %d records  %d KB" % (out_pcb, len(out), os.path.getsize(out_pcb)//1024))
    for k2, (n, a) in stats.items():
        print("  %-12s %5d rects  %7.1f mm2" % (k2, n, a))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
