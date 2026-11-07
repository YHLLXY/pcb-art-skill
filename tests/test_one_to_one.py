# -*- coding: utf-8 -*-
"""1:1 实尺页（21-one_to_one）：尺寸算错就等于白做，三条不变量必须钉住。

这块板子是"96 mm 的方板转 45°"——外接 99.34 mm（72 版）而不是 96，也不是 135.76。
外接框算法错一个数，打出来就是一张错尺度的纸，而它存在的唯一意义就是"尺度"。
"""
import math

import pytest

from conftest import load

m = load('o2o', '21-one_to_one.py')


def test_bbox_square_no_rot():
    assert m.rounded_rect_bbox(96, 96, 3, 0) == pytest.approx((96, 96))


def test_bbox_square_rot45():
    """72x72 R3 转 45°：99.3381（实测 GKO 中心线 bbox 同值）；不是 72、也不是 101.8。"""
    w, h = m.rounded_rect_bbox(72, 72, 3, 45)
    assert w == pytest.approx(99.3381, abs=1e-3)
    assert h == pytest.approx(99.3381, abs=1e-3)


def test_bbox_rot45_no_radius_is_diag():
    w, h = m.rounded_rect_bbox(72, 72, 0, 45)
    assert w == pytest.approx(72 * math.sqrt(2), abs=1e-6)


def test_area_matches_measured():
    """72 板：L²-(4-π)r² = 5176.27；13-check 在 Gerber 上量到 5176.24。"""
    assert m.board_area(72, 72, 3) == pytest.approx(5176.27, abs=0.05)
    assert m.board_area(96, 96, 3) == pytest.approx(9208.27, abs=0.05)


def test_mass_is_grams_not_kilograms():
    """面积 mm² × 厚 mm = mm³，要 /1000 变 cm³ 再乘 1.85。漏了 /1000 就是 27 kg。"""
    assert m.mass_g(9208.27) == pytest.approx(27.26, abs=0.05)
    assert m.mass_g(5176.27) == pytest.approx(15.32, abs=0.05)
