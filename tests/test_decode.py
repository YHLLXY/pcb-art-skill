# -*- coding: utf-8 -*-
"""徽记解码要能认任意两主色（04 第 98 条的判原型，靠的就是这一步）。

以前写死了"蓝/橙"阈值，换一张红/金的徽记就判不出来。现在按不透明像素做阈值聚类。
"""
import re
import subprocess
import sys

import pytest

from conftest import ROOT, EXAMPLES, SCRIPTS

BADGE = EXAMPLES / "uestc70" / "badge.png"


def decode(img):
    r = subprocess.run([sys.executable, str(SCRIPTS / "00-decode_badge.py"), str(img), "30"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_uestc_blue_orange():
    if not BADGE.exists():
        pytest.skip("校徽不在（不在 MIT 内，可删可换）")
    out = decode(BADGE)
    assert "圆盘型" in out
    assert "511.5 px / 15.00 mm" in out      # 外圆
    assert "317.3 px / 9.30 mm" in out       # 内圆
    assert re.search(r"环带实色率\s+89\.9%", out)
    assert "#004098" in out                  # 主色被识别成深蓝，不再靠魔法数


def test_red_gold(tmp_path):
    """红盘 + 金内圆：没有任何蓝/橙像素，也必须判成圆盘型。"""
    from PIL import Image, ImageDraw
    S, c = 1024, 512
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([c - 500, c - 500, c + 500, c + 500], fill=(200, 30, 40, 255))
    d.ellipse([c - 300, c - 300, c + 300, c + 300], fill=(230, 170, 40, 255))
    p = tmp_path / "red-gold.png"
    im.save(p)
    out = decode(p)
    assert "圆盘型" in out
    assert "#C81E28" in out
    assert "#E6AA28" in out
