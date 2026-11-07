# -*- coding: utf-8 -*-
"""面积与收费（22-area_budget）：这类错误的特点是"数字看起来对"，只有分母错了。

真实事故：用户说"沉金超过 20 平方厘米了"，我们实测 10.16 cm²(19.62%)。
原因是把 19.62% 乘了**外接方框** 99.18 cm² —— 菱形只占外框 52%，凭空翻了一倍。
所以这里钉死：周长、轮廓面积、外接框面积、沉金分级收费。
"""
import math

import pytest

from conftest import load

m = load('area', '22-area_budget.py')


def test_perimeter_rounded_square():
    """72x72 R3：4*(72-6) + 2π*3 = 282.85。板边金带面积 = 线宽 x 周长，全靠这个数。"""
    assert m.perimeter(72, 72, 3) == pytest.approx(282.85, abs=0.01)


def test_perimeter_no_radius():
    assert m.perimeter(86.25, 54.25, 0) == pytest.approx(2*(86.25+54.25), abs=1e-9)


def test_diamond_area_vs_bbox():
    """菱形板：外框面积是板面积的 1.9 倍。用外框当分母，比例会掉一半。"""
    a = m.board_area(72, 72, 3)
    bw, bh = m.rounded_rect_bbox(72, 72, 3, 45)
    assert a == pytest.approx(5176.27, abs=0.05)
    assert bw == pytest.approx(99.3381, abs=1e-3)
    assert (bw*bh)/a == pytest.approx(1.91, abs=0.01)


def test_enig_fee_below_threshold():
    """14.38% < 30%：不超线，单价就是 140 元/㎡；51.76 cm² 的板子 0.72 元/片。"""
    fee, unit, over = m.enig_fee(5176.24, 14.38)
    assert over == 0
    assert unit == pytest.approx(140.0)
    assert fee == pytest.approx(0.7247, abs=1e-3)


def test_enig_fee_above_threshold():
    """公告例子：60% 的 1U" 沉金 → 140 + 30*5.6 = 308 元/㎡（不是只对金的部分加收）。"""
    fee, unit, over = m.enig_fee(1e6, 60.0, "1U")
    assert over == pytest.approx(30.0)
    assert unit == pytest.approx(308.0)
    assert fee == pytest.approx(308.0)


def test_enig_2u_is_double_rate():
    _, unit, _ = m.enig_fee(1e6, 60.0, "2U")
    assert unit == pytest.approx(240.0 + 30*11.2)


def test_band_share():
    """金带 1.0 mm x 周长 282.85 = 282.85 mm²，占 7.45 cm² 沉金的 38%。"""
    band = 1.0*m.perimeter(72, 72, 3)
    assert band/m.board_area(72, 72, 3)*100 == pytest.approx(5.46, abs=0.02)
