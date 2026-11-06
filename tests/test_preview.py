# -*- coding: utf-8 -*-
"""spec 预览（20-preview_spec）：这个脚本栽过两次坐标约定的跟头，必须有测试钉住。

两次都是同一个类别的错：epcb2 里 POLY 的 path 是扁平的 [R,...]（FILL 才是嵌套 [[...]]），
而且 R 的第二个数是 top、FILL 的第二个数是 y_center。写反了会画出"横条纹徽记"——图还能出，只是全错。
"""
import subprocess
import sys

import pytest

from conftest import ROOT, EXAMPLES, TEMPLATE, SCRIPTS

SPEC = EXAMPLES / 'uestc70' / 'spec.json'


@pytest.fixture(scope='module')
def rendered(tmp_path_factory):
    out = tmp_path_factory.mktemp('prev') / 'mock.png'
    r = subprocess.run([sys.executable, str(SCRIPTS / '20-preview_spec.py'),
                        str(SPEC), str(TEMPLATE), str(out), '--sc', '8'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if '找不到字体' in (r.stdout + r.stderr):
        pytest.skip('本机没有行楷字体（用户自备）')
    assert r.returncode == 0, r.stdout + r.stderr
    from PIL import Image
    return Image.open(out).convert('RGB')


def test_size(rendered):
    # 画布 = 板尺寸 + 8 mm 边，@8 px/mm
    assert rendered.width == int((86.2 + 8) * 8)
    assert rendered.height == int((54.2 + 8) * 8)


def test_badge_disc_is_gold(rendered):
    """徽记盘心（0, 8 mm）必须是金的：坐标约定写错时这里会是暗的或条纹。"""
    sc = 8.0
    X0, Y0 = -(86.2 + 8) / 2.0, (54.2 + 8) / 2.0
    px = int((0 - X0) * sc); py = int((Y0 - 8.0) * sc)
    r, g, b = rendered.getpixel((px, py))
    assert r > 150 and g > 120 and b < 160, (r, g, b)


def test_badge_bbox(rendered):
    """金盘的外接框必须是 φ30 左右、居中在 x=0。

    这条才是真正钉住坐标约定的：把 FILL 的 left 当成 center（每块都左移半个宽度）时，
    盘心可能还是金的、角上还是暗的，但**外接框会变宽并向左跑**，肉眼不一定看得出。
    """
    import numpy as np
    sc = 8.0
    X0, Y0 = -(86.2 + 8) / 2.0, (54.2 + 8) / 2.0
    a = np.asarray(rendered).astype(int)
    # 只看徽记窗口：x -18..18 mm，y -8..24 mm（避开板边金带）
    x1, x2 = int((-18 - X0) * sc), int((18 - X0) * sc)
    y1, y2 = int((Y0 - 24) * sc), int((Y0 + 8) * sc)
    win = a[y1:y2, x1:x2]
    gold = (win[:, :, 0] > 150) & (win[:, :, 1] > 120) & (win[:, :, 2] < 160)
    ys, xs = np.nonzero(gold)
    assert len(xs) > 1000, len(xs)
    w_mm = (xs.max() - xs.min()) / sc
    cx_mm = ((xs.min() + xs.max()) / 2.0) / sc - 18.0
    assert abs(w_mm - 30) < 2.0, w_mm
    assert abs(cx_mm) < 1.0, cx_mm


def test_empty_area_is_dark(rendered):
    """徽记外、板内的一角不应该是金的，也不该是白的。"""
    sc = 8.0
    X0, Y0 = -(86.2 + 8) / 2.0, (54.2 + 8) / 2.0
    px = int((30 - X0) * sc); py = int((Y0 + 20) * sc)
    r, g, b = rendered.getpixel((px, py))
    assert r < 120 and g < 120, (r, g, b)
