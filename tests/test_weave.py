# -*- coding: utf-8 -*-
"""织纹测试：条数/面积/朝向三件事都要锁。

朝向是最容易错、也最看不出来的一项（04 第 110 条：行序不翻 → 上下镜像，肉眼无感）。
所以这里不测"像不像"，直接按单元算 H/V 和 PATTERN 对。
"""
import math

import pytest

from conftest import load

wv = load("weave15", "15-weave.py")
CELL = wv.CELL


def cell_votes(rects, cell, i0, j0, ni, nj):
    """把每条矩形和单元的交集面积记到 H / V 账上。

    不能靠"采样点命中"判朝向：条纹间距 0.195、线宽 0.103，随便取的点大半落在缝里，
    会得到"没覆盖 = 默认 H"这种假结论（第一版就这么误判了一整行）。
    """
    import numpy as np
    H = np.zeros((nj, ni)); V = np.zeros((nj, ni))
    for (l, yc, w, h) in rects:
        ax, bx = l, l + w
        ay, by = yc - h / 2.0, yc + h / 2.0
        si0, si1 = int(math.floor(ax / cell)), int(math.floor((bx - 1e-9) / cell))
        sj0, sj1 = int(math.floor(ay / cell)), int(math.floor((by - 1e-9) / cell))
        for j in range(max(sj0, j0), min(sj1, j0 + nj - 1) + 1):
            oy = min(by, (j + 1) * cell) - max(ay, j * cell)
            if oy <= 0: continue
            for i in range(max(si0, i0), min(si1, i0 + ni - 1) + 1):
                ox = min(bx, (i + 1) * cell) - max(ax, i * cell)
                if ox <= 0: continue
                (H if w >= h else V)[j - j0, i - i0] += ox * oy
    return H, V


def test_default_clip():
    rs = wv.weave_rects()
    assert len(rs) == 5416
    assert abs(sum(w * h for _, _, w, h in rs) - 2086) < 5


def test_example_clip():
    rs = wv.weave_rects(42.55, 25.55, 2.9)
    assert len(rs) == 5749
    assert abs(sum(w * h for _, _, w, h in rs) - 2239.0) < 5


def test_orientation_matches_pattern():
    """在离屏区域（|x|<=16, |y|<=10）逐单元比：生成出来的朝向必须等于 PATTERN，0 个例外。"""
    import numpy as np
    rs = wv.weave_rects(42.55, 25.55, 2.9)
    i0, j0, ni, nj = -8, -5, 16, 10
    H, V = cell_votes(rs, CELL, i0, j0, ni, nj)
    bad = []
    for jj in range(nj):
        for ii in range(ni):
            i, j = i0 + ii, j0 + jj
            cover = H[jj, ii] + V[jj, ii]
            assert cover > 0.2 * CELL * CELL, "单元 (%d,%d) 没被织纹盖住，覆盖率不对" % (i, j)
            got = "H" if H[jj, ii] >= V[jj, ii] else "V"
            # 期望值在这里独立算一遍：表按「图像方向」写，第 0 行在最高处，
            # 而 j 从 y=0 往上数，所以行号要翻 (4-j%4)%4（04 第 110 条）。
            # 不能调 wv.orient() —— 那样实现错了测试也跟着错（第一次写就踩了这个坑）。
            want = wv.PATTERN[(4 - j % 4) % 4][i % 4]
            if got != want:
                bad.append((i, j, want, got))
    assert not bad, "单元朝向不符：%s" % bad[:8]


def test_pitch_and_width():
    """条数对不代表间距对：0.195 和 0.200 的条数一样（每 2 mm 都 10 条），只有间距能分开。"""
    rs = wv.weave_rects(42.55, 25.55, 2.9)
    # 取第 0 行（y 0..2）里所有横条，量它们的 y 间距
    hs = sorted({round(yc, 6) for (l, yc, w, h) in rs if w > h and 0 < yc < 2})
    assert len(hs) >= 9
    gaps = [b - a for a, b in zip(hs, hs[1:])]
    assert all(abs(g - wv.PITCH) < 1e-6 for g in gaps), gaps
    widths = {round(h, 6) for (l, yc, w, h) in rs if w > h}
    assert widths == {round(wv.LINE_W, 6)}, widths


def test_pattern_matches_checker():
    """13-check 里自己抄了一份纹路表，两份必须一样，否则自检和生成各说各话。"""
    from conftest import SCRIPTS
    src = (SCRIPTS / "13-check.py").read_text(encoding="utf-8")
    for row in wv.PATTERN:
        assert '"%s"' % row in src, "13-check 的 WEAVE_REF 缺 %s" % row
