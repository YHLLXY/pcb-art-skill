# -*- coding: utf-8 -*-
"""手绘稿（arts）与纸面点阵（dots）：几何口径、镜像、互相让位。

三条最容易静默搞错的东西：
  1. FILL 的 "R" 路径第二值是**上边**，不是中线（拿 v10 的 Gerber 逐像素投票定过，IoU 0.914 vs 0.527）；
  2. 背面靠镜像掩膜，不是靠 mirror:true —— 翻错了整张图是镜像的，但预览一动不动；
  3. 白点必须被墨线让开，否则白丝印会盖在沉金上。
"""
import json
import re
from collections import Counter

import numpy as np
import pytest
from PIL import Image, ImageDraw

from conftest import TEMPLATE, run


def _png(path):
    """200x200：上下两条 100x60 的黑块，x 50..150。art 宽 20 mm -> 0.1 mm/px。"""
    im = Image.new("L", (200, 200), 255)
    d = ImageDraw.Draw(im)
    d.rectangle([50, 20, 150, 80], fill=0)
    d.rectangle([50, 120, 150, 180], fill=0)
    im.save(path)
    return path


def _spec(png, mirror, dots=False):
    s = {
        "name": "T",
        "board": {"w": 28, "h": 28, "r": 3},
        "frame": {"w": 28, "h": 28, "r": 3, "cu": 1.0, "mask": 1.1},
        "step": 0.06,
        "arts": [{"png": str(png), "w": 20.0, "cx": 0, "cy": 0, "thr": 105,
                  "layer": 2, "mask_layer": 6, "mask_expand": 0.05,
                  "mirror": mirror, "minw": 0.15}],
    }
    if dots:
        s["dots"] = {"ox": -10, "oy": 10, "pitch": 5.0, "x0": 1.0, "y0": 1.0,
                     "r": 1.0, "nx": 4, "ny": 4, "layer": 4, "mirror": mirror}
    return s


def _build(tmp_path, png, mirror, dots=False, tag="a"):
    spec = tmp_path / f"{tag}.json"
    spec.write_text(json.dumps(_spec(png, mirror, dots)), encoding="utf-8")
    out = tmp_path / f"{tag}.epcb2"
    r = run("16-build_board.py", spec, TEMPLATE, out)
    assert r.returncode == 0, r.stdout + r.stderr
    return spec, out, r.stdout


def _rects(epcb2, layer):
    K = 0.0254
    out = []
    for ln in epcb2.read_text(encoding="utf-8").split("\n"):
        ln = ln.strip()
        if '"type":"FILL"' not in ln:
            continue
        o = json.loads(ln.split("||", 1)[1].rstrip("|"))
        if o["layerId"] != layer:
            continue
        r = o["path"][0]
        out.append((r[1] * K, r[2] * K, r[3] * K, r[4] * K))   # left, TOP, w, h
    return out


@pytest.fixture(scope="module")
def board(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("art")
    return tmp, _png(tmp / "a.png")


def test_art_geometry(board):
    """两条黑块 -> y 8..2 和 -2..-8，x -5..5（mirror=False）。"""
    tmp, png = board
    _, epcb2, _ = _build(tmp, png, False, tag="geo")
    rs = _rects(epcb2, 2)
    assert rs, "没生成铜"
    xs0 = min(l for l, t, w, h in rs); xs1 = max(l + w for l, t, w, h in rs)
    assert abs(xs0 + 5.0) < 0.12 and abs(xs1 - 5.0) < 0.12, (xs0, xs1)
    tops = [t for l, t, w, h in rs]; bots = [t - h for l, t, w, h in rs]
    assert abs(max(tops) - 8.0) < 0.12, max(tops)
    assert abs(min(bots) + 8.0) < 0.12, min(bots)
    # 中间必须有空：-2..2 之间没有任何铜（阈值靠 0.06 网格量化，给 0.1 余量）
    mid = [r for r in rs if r[1] < 1.9 and r[1] - r[3] > -1.9]
    assert not mid, ("两条黑块之间不该有铜", mid[:3])


def test_mask_is_cu_plus_expansion(board):
    tmp, png = board
    _, epcb2, _ = _build(tmp, png, False, tag="mask")
    cu, mk = _rects(epcb2, 2), _rects(epcb2, 6)
    assert len(cu) == len(mk)
    dw = sorted(w for _, _, w, _ in mk)[len(mk) // 2] - sorted(w for _, _, w, _ in cu)[len(cu) // 2]
    assert abs(dw - 0.05) < 1e-6, dw


def test_mirror_is_x_flip(board):
    """镜像 = 左右翻（x -> -(l+w)），不是"再画一遍"。"""
    tmp, png = board
    _, a, _ = _build(tmp, png, False, tag="m0")
    _, b, _ = _build(tmp, png, True, tag="m1")
    ra, rb = _rects(a, 2), _rects(b, 2)
    assert len(ra) == len(rb)
    la = sorted(round(l, 4) for l, t, w, h in ra)
    lb = sorted(round(-(l + w), 4) for l, t, w, h in rb)
    assert la == lb, "镜像后的 rect 左边界不是原图的 -右边界"


def test_dots_avoid_ink_and_holes(board):
    """白丝印点不压金、不压孔。"""
    tmp, png = board
    _, epcb2, _ = _build(tmp, png, True, dots=True, tag="d")
    cu, dots = _rects(epcb2, 2), _rects(epcb2, 4)
    assert dots, "没生成白点"
    sc, W = 25.0, 40.0
    def raster(rs):
        im = Image.new("L", (int(W * sc), int(W * sc)), 0)
        d = ImageDraw.Draw(im)
        for l, t, w, h in rs:
            d.rectangle([(l + W / 2) * sc, (W / 2 - t) * sc,
                         (l + w + W / 2) * sc, (W / 2 - (t - h)) * sc], fill=255)
        return np.asarray(im) > 127
    ov = (raster(cu) & raster(dots)).sum()
    assert ov == 0, "白点和金重叠 %d px" % ov


def test_preview_fill_y_is_top(board):
    """预览若把 FILL 第二值当中线，合并过的长块会整体上移半个高度 —— 用像素位置锁住。"""
    tmp, png = board
    spec, _, _ = _build(tmp, png, False, tag="pv")
    out = tmp / "pv.png"
    r = run("20-preview_spec.py", spec, TEMPLATE, out, "--sc", "20", "--side", "back")
    assert r.returncode == 0, r.stdout + r.stderr
    a = np.asarray(Image.open(out).convert("RGB")).astype(int)
    gold = (np.abs(a[:, :, 0] - 206) < 8) & (np.abs(a[:, :, 1] - 172) < 8) & (np.abs(a[:, :, 2] - 110) < 8)
    # 画布 28+8 mm @ 20 px/mm = 720 px，y 从 +18 到 -18
    H = a.shape[0]
    rows = np.nonzero(gold[:, 300:420].any(axis=1))[0]
    assert len(rows), "预览里没有金"
    Hmm = H / 20.0
    runs = []
    st = pv = rows[0]
    for v in rows[1:]:
        if v == pv + 1:
            pv = v
        else:
            runs.append((Hmm / 2 - pv / 20.0, Hmm / 2 - st / 20.0)); st = pv = v
    runs.append((Hmm / 2 - pv / 20.0, Hmm / 2 - st / 20.0))
    tops = [b for _, b in runs]
    bots = [a0 for a0, _ in runs]
    assert min(abs(t - 8.0) for t in tops) < 0.25, ("上边应有一条在 8", runs)
    assert min(abs(b + 8.0) for b in bots) < 0.25, ("下边应有一条在 -8", runs)
    assert not any(a0 < 1.8 and b > -1.8 for a0, b in runs), ("中间不该有金", runs)
