# -*- coding: utf-8 -*-
"""素材链路：采集（17）→ 粗筛成图墙（18）。

纪律：机器只做采集与粗筛，审美交给人。所以测试只锁「能不能上板」这条判据，
不锁「好不好看」——后者没有断言。
"""
import re
import subprocess
import sys

import pytest

from conftest import SCRIPTS


def make(dir_, name, size, bg, fg=None, width=20, tiny=False):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", size, bg)
    if fg:
        d = ImageDraw.Draw(im)
        d.ellipse([size[0] // 10, size[1] // 10, size[0] * 9 // 10, size[1] * 9 // 10],
                  outline=fg, width=width)
    p = dir_ / name
    im.save(p)
    return p


def run(script, *a):
    return subprocess.run([sys.executable, str(SCRIPTS / script)] + [str(x) for x in a],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_crawl_local_then_filter(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    make(src, "good.png", (1024, 1024), (0, 0, 0, 0), (0, 0, 0, 255), 26)
    make(src, "dark-small.png", (300, 300), (30, 30, 40, 255), (255, 255, 255, 255), 3)
    out = tmp_path / "cand"

    r = run("17-crawl_assets.py", "--from-dir", src, "--out", out)
    assert r.returncode == 0, r.stderr
    assert (out / "good.png").exists()
    assert (out / "meta.json").exists()
    assert "![](" in (out / "index.md").read_text(encoding="utf-8")

    r = run("18-filter_assets.py", out, "--target-mm", "40")
    assert r.returncode == 0, r.stderr
    md = (out / "index.md").read_text(encoding="utf-8")
    assert re.search(r"\| good\.png \| \d+ \| ✅ 可用", md), md
    # 2 KB 的小图 17 直接跳过（复制过来只会污染图墙），这条也要锁住
    assert not (out / "dark-small.png").exists()


def test_dark_small_is_rejected(tmp_path):
    """300 px + 暗底 + 细线：三条都要报出来（这条是"照片/截图开不了工"的典型）。"""
    d = tmp_path / "d"; d.mkdir()
    make(d, "bad.png", (300, 300), (30, 30, 40, 255), (255, 255, 255, 255), 3)
    r = run("18-filter_assets.py", d, "--target-mm", "40")
    md = (d / "index.md").read_text(encoding="utf-8")
    assert "小于 800 px" in md
    assert "有色背景" in md
    assert "❌ 剔" in md
