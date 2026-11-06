# -*- coding: utf-8 -*-
"""20-preview_spec.py —— 看 spec 长什么样，不用开 EDA

spec → .epcb2 之后，把里面的 FILL/POLY/STRING 按层画成位图：
黑底（哑黑）、铜（被盖住 = 深褐近黑）、金（铜 ∧ 开窗）、白（丝印）、孔（暗圆）。

这不是 3D，也不是最终效果；它只回答"元素在不在该在的地方、比例对不对"。
真正的材质/浮雕看 `14-render3d.py`（要 Gerber）。

用法:
  python 20-preview_spec.py <spec.json> <模板工程目录> <out.png> [--sc 20] [--side front|back]
"""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
K = 0.0254

def main(spec_path, tpl_dir, out_png, sc=20.0, side="front"):
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    tmp = os.path.join(os.path.dirname(os.path.abspath(out_png)), "_preview.epcb2")
    r = subprocess.run([sys.executable, os.path.join(HERE, "16-build_board.py"),
                        spec_path, tpl_dir, tmp], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout + r.stderr); sys.exit(1)

    spec = json.load(open(spec_path, encoding="utf-8"))
    W = float(spec.get("frame", {}).get("w") or spec["board"]["w"]) + 8.0
    H = float(spec.get("frame", {}).get("h") or spec["board"]["h"]) + 8.0
    X0, Y0 = -W / 2.0, H / 2.0
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

    for ln in open(tmp, encoding="utf-8"):
        ln = ln.strip()
        if not ln: continue
        t = re.search(r'"type":"([^"]+)"', ln).group(1)
        if t == "POLY":
            o = json.loads(ln.split("||", 1)[1].rstrip("|"))
            lay = o["layerId"]
            if lay not in (CU, MASK): continue
            # POLY 的 path 是扁平的 ["R",...]；FILL 的是嵌套 [[...]]，两种都接
            p = o["path"]
            if p and isinstance(p[0], list): p = p[0]
            if not isinstance(p, list) or p[0] != "R" or len(p) < 7: continue
            # epcb2 的 R 路径是 [left, top, w, h, rot, r]（top 是上边，不是中心）
            l, t = p[1] * K, p[2] * K
            w = p[3] * K; h = p[4] * K
            rad = (p[6] if len(p) > 6 else 0) * K
            lw = o.get("width", 0) * K
            box = [P(l, t), P(l + w, t - h)]
            if lay == 11:                      # 板框：只画一条灰线，用来判断"金带是否压板框"
                ImageDraw.Draw(im).rounded_rectangle(box, radius=rad * sc, outline=(150, 150, 150), width=1)
                continue
            tgt = cu_layer if lay == CU else mk_layer
            ImageDraw.Draw(tgt).rounded_rectangle(box, radius=rad * sc, outline=255, width=max(1, int(lw * sc)))
        elif t == "FILL":
            o = json.loads(ln.split("||", 1)[1].rstrip("|"))
            lay = o["layerId"]
            if lay not in (CU, MASK, SILK): continue
            rhs = o["path"]
            if rhs and isinstance(rhs[0], list): rhs = rhs[0]
            if not isinstance(rhs, list) or rhs[0] != "R" or len(rhs) < 7: continue
            # FILL 的 R 路径是 [left, y_center, w, h, rot, r]
            l, cy = rhs[1] * K, rhs[2] * K
            w, h = rhs[3] * K, rhs[4] * K
            box = [P(l, cy + h / 2.0), P(l + w, cy - h / 2.0)]
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
            d.ellipse([P(cx - pr, cy + pr), P(cx + pr, cy - pr)], fill=(206, 172, 110))
            d.ellipse([P(cx - rr, cy + rr), P(cx + rr, cy - rr)], fill=(12, 12, 12))

    cu = cu_layer.load(); mk = mk_layer.load(); sk = sk_layer.load()
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            g = mk[x, y] > 0 and cu[x, y] > 0
            if sk[x, y] > 0:      px[x, y] = (238, 238, 232)
            elif g:               px[x, y] = (206, 172, 110)
            elif cu[x, y] > 0:    px[x, y] = (40, 36, 32)
    try: os.remove(tmp)
    except OSError: pass
    im.save(out_png)
    print("preview ->", out_png, "%dx%d @ %.0f px/mm" % (im.width, im.height, sc))

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 3:
        print(__doc__); sys.exit(2)
    sc = 20.0; side = "front"
    if "--sc" in a: i = a.index("--sc"); sc = float(a[i + 1]); del a[i:i + 2]
    if "--side" in a:
        i = a.index("--side"); side = a[i + 1]; del a[i:i + 2]
    main(a[0], a[1], a[2], sc, side)
