# -*- coding: utf-8 -*-
"""20-preview_spec.py —— 看 spec 长什么样，不用开 EDA

spec → .epcb2 之后，把里面的 FILL/POLY/STRING 按层画成位图：
黑底（哑黑）、铜（被盖住 = 深褐近黑）、金（铜 ∧ 开窗）、白（丝印）、孔（暗圆）。

这不是 3D，也不是最终效果；它只回答"元素在不在该在的地方、比例对不对"。
真正的材质/浮雕看 `14-render3d.py`（要 Gerber）。

用法:
  python 20-preview_spec.py <spec.json> <模板工程目录> <out.png> [--sc 20] [--side front|back] [--flip]
                            [--crop x0,y0,x1,y1]   # 局部：--sc 60 --crop -5,20,15,40
"""
import json, math, os, re, subprocess, sys
from PIL import Image, ImageDraw

def rrect_pts(l, t, w, h, rot=0.0, r=0.0, seg=9):
    """圆角矩形 -> 多边形点列（mm，y 向上）。

    EDA 的 rot 是绕 (l, t) 这个参考角转的（实测，见 04 第 126 条），
    所以这里也绕同一个点转，预览才和真实导出对得上。
    """
    r = max(0.0, min(r, w/2.0, h/2.0))
    if r <= 1e-9:
        pts = [(l, t), (l+w, t), (l+w, t-h), (l, t-h)]
    else:
        pts = []
        # 顺时针：上边 -> 右上角 -> 右边 -> 右下角 -> 下边 -> 左下角 -> 左边 -> 左上角
        corners = [
            (l+w-r, t-r,  90.0),   # 右上，圆心
            (l+w-r, t-h+r,  0.0),  # 右下
            (l+r,   t-h+r, -90.0), # 左下
            (l+r,   t-r,  -180.0), # 左上
        ]
        for (cx, cy, a0) in corners:
            for i in range(seg+1):
                a = math.radians(a0 - 90.0*i/seg)
                pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    if rot:
        th = math.radians(rot)
        c, s = math.cos(th), math.sin(th)
        pts = [(l + (x-l)*c - (y-t)*s, t + (x-l)*s + (y-t)*c) for (x, y) in pts]
    return pts

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
K = 0.0254

def main(spec_path, tpl_dir, out_png, sc=20.0, side="front", flip=False, crop=None):
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    tmp = os.path.join(os.path.dirname(os.path.abspath(out_png)), "_preview.epcb2")
    r = subprocess.run([sys.executable, os.path.join(HERE, "16-build_board.py"),
                        spec_path, tpl_dir, tmp], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout + r.stderr); sys.exit(1)

    spec = json.load(open(spec_path, encoding="utf-8"))
    _f = spec.get("frame") or spec["board"]
    _bw = float(_f["w"]); _bh = float(_f["h"])
    _rot = math.radians(float(_f.get("rot", spec["board"].get("rot", 0)) or 0))
    # 转了角度的板，画布要按旋转后的外接框算，否则菱形会被裁掉四个角
    W = _bw * abs(math.cos(_rot)) + _bh * abs(math.sin(_rot)) + 8.0
    H = _bw * abs(math.sin(_rot)) + _bh * abs(math.cos(_rot)) + 8.0
    X0, Y0 = -W / 2.0, H / 2.0
    if crop:                                  # --crop x0,y0,x1,y1（mm）出 60 px/mm 局部图
        X0, Y0, W, H = crop[0], crop[3], crop[2] - crop[0], crop[3] - crop[1]
    im = Image.new("RGB", (int(W * sc), int(H * sc)), (26, 26, 28))
    d = ImageDraw.Draw(im)
    # 层 → 颜色（按"成品外观"而不是按层名）
    CU, MASK, SILK = 1, 5, 3
    if side == "back":
        CU, MASK, SILK = 2, 6, 4
    cu_layer = Image.new("L", im.size, 0)
    mk_layer = Image.new("L", im.size, 0)
    sk_layer = Image.new("L", im.size, 0)

    def P(x, y):
        return ((x - X0) * sc, (Y0 - y) * sc)

    pads = []
    board_pts = []
    for ln in open(tmp, encoding="utf-8"):
        ln = ln.strip()
        if not ln: continue
        t = re.search(r'"type":"([^"]+)"', ln).group(1)
        if t == "POLY":
            o = json.loads(ln.split("||", 1)[1].rstrip("|"))
            lay = o["layerId"]
            if lay not in (CU, MASK, 11, 1, 2): continue
            # POLY 的 path 是扁平的 ["R",...]；FILL 的是嵌套 [[...]]，两种都接
            p = o["path"]
            if p and isinstance(p[0], list): p = p[0]
            if not isinstance(p, list) or p[0] != "R" or len(p) < 7: continue
            # epcb2 的 R 路径是 [left, top, w, h, rot, r]（top 是上边；rot 绕 left/top 转）
            l, tp = p[1] * K, p[2] * K
            w = p[3] * K; h = p[4] * K
            rot = float(p[5]) if len(p) > 5 else 0.0
            rad = (p[6] if len(p) > 6 else 0) * K
            lw = o.get("width", 0) * K
            pts = [P(x, y) for (x, y) in rrect_pts(l, tp, w, h, rot, rad)]
            pts.append(pts[0])
            if lay == 11:                      # 板框：灰线 + 记住轮廓（后面把各层裁进板内）
                board_pts[:] = pts
                ImageDraw.Draw(im).line(pts, fill=(150, 150, 150), width=1, joint="curve")
                continue
            if lay not in (CU, MASK): continue
            tgt = cu_layer if lay == CU else mk_layer
            ImageDraw.Draw(tgt).line(pts, fill=255, width=max(1, int(round(lw * sc))),
                                     joint="curve")
        elif t == "FILL":
            o = json.loads(ln.split("||", 1)[1].rstrip("|"))
            lay = o["layerId"]
            if lay not in (CU, MASK, SILK): continue
            rhs = o["path"]
            if rhs and isinstance(rhs[0], list): rhs = rhs[0]
            if not isinstance(rhs, list) or rhs[0] != "R" or len(rhs) < 7: continue
            # FILL 的 R 路径和 POLY 一样是 [left, top, w, h, rot, r] —— 第二值是上边，不是中线。
            # 这条是拿 v10 的 Gerber 逐像素投票投出来的（top 口径 IoU 0.914 / center 0.509），
            # 写成 center 会让所有合并过的长块整体上移半个高度（0.06 的行看不出来，2 mm 的块差 1 mm）。
            l, t = rhs[1] * K, rhs[2] * K
            w, h = rhs[3] * K, rhs[4] * K
            box = [P(l, t), P(l + w, t - h)]
            # 外扩 0.5 px：扫描线相邻两行在低分辨率下会漏出一条亚像素缝（假缺陷）
            box = [box[0][0] - 0.5, box[0][1] - 0.5, box[1][0] + 0.5, box[1][1] + 0.5]
            tgt = cu_layer if lay == CU else (mk_layer if lay == MASK else sk_layer)
            ImageDraw.Draw(tgt).rectangle(box, fill=255)
        elif t == "STRING":
            # 文本对象在 EDA 里才生成字形；预览只画"占多长的条"（字宽实测 ≈0.617×size）
            o = json.loads(ln.split("||", 1)[1].rstrip("|"))
            lay = o["layerId"]
            if lay not in (CU, MASK, SILK, 4, 2, 6): continue
            size_mm = o["fontSize"] * K
            L = len(o["text"]) * 0.617 * size_mm
            x0, y0 = o["x"] * K, o["y"] * K
            box = [P(x0, y0 + size_mm), P(x0 + L, y0)]
            col = (150, 150, 150)
            if lay in (CU, 2): col = (120, 100, 70)
            if lay in (SILK, 4): col = (200, 200, 196)
            ImageDraw.Draw(im).rectangle(box, outline=col, width=1)
            if L > 6:
                ImageDraw.Draw(im).text((box[0][0] + 2, box[0][1] + 2), o["text"][:28], fill=col)
        elif t == "PAD":
            o = json.loads(ln.split("||", 1)[1].rstrip("|"))
            cx, cy = o["centerX"] * K, o["centerY"] * K
            rr = o["hole"]["width"] * K / 2.0
            pr = (o.get("defaultPad", {}).get("width") or o["hole"]["width"]) * K / 2.0
            pads.append((cx, cy, rr, pr))

    # 各层裁进板内：铜/丝印本来就会画出板外（参考板是故意出血的），
    # 不裁的话预览会把板外的纹理也画出来，看着像"板子是方的"。
    if len(board_pts) >= 3:
        bm = Image.new("L", im.size, 0)
        ImageDraw.Draw(bm).polygon(board_pts, fill=255)
        for lay in (cu_layer, mk_layer, sk_layer):
            lay.paste(0, (0, 0), Image.eval(bm, lambda v: 255 - v))
    cu = cu_layer.load(); mk = mk_layer.load(); sk = sk_layer.load()
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            g = mk[x, y] > 0 and cu[x, y] > 0
            if sk[x, y] > 0:      px[x, y] = (238, 238, 232)
            elif g:               px[x, y] = (206, 172, 110)
            elif cu[x, y] > 0:    px[x, y] = (34, 32, 30)   # 铜被哑黑盖住：只比黑色亮一点点
    # 焊盘最后画：铜层（尤其织纹）会铺满整块板，先画会被 per-pixel 合成盖掉，
    # 结果 φ3 挂绳孔在预览里"看不见"（v1 就是这么被骗过去的）。
    for (cx, cy, rr, pr) in pads:
        d.ellipse([P(cx - pr, cy + pr), P(cx + pr, cy - pr)], fill=(206, 172, 110))
        d.ellipse([P(cx - rr, cy + rr), P(cx + rr, cy - rr)], fill=(12, 12, 12))
    try: os.remove(tmp)
    except OSError: pass
    if flip:                      # 背面：翻过来看，字才是正的（数据本身是镜像的）
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im.save(out_png)
    print("preview ->", out_png, "%dx%d @ %.0f px/mm%s" % (
        im.width, im.height, sc, "  (mirrored)" if flip else ""))

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 3:
        print(__doc__); sys.exit(2)
    sc = 20.0; side = "front"; flip = False; crop = None
    if "--sc" in a: i = a.index("--sc"); sc = float(a[i + 1]); del a[i:i + 2]
    if "--side" in a:
        i = a.index("--side"); side = a[i + 1]; del a[i:i + 2]
    if "--flip" in a: i = a.index("--flip"); flip = True; del a[i]
    if "--crop" in a:
        i = a.index("--crop"); crop = [float(v) for v in a[i+1].split(",")]; del a[i:i+2]
    main(a[0], a[1], a[2], sc, side, flip, crop)
