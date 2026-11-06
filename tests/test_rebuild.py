# -*- coding: utf-8 -*-
"""金板复现：examples/uestc70/spec.json → .epcb2，数字必须和交付时一致。

这些数字是 2026-11-06 用当时的 spec + 华文行楷实测的（docs/06-Skill收尾计划.md 2.1）。

**改坏了要红，不许为了让测试变绿去改断言。** 换了字体或改了 spec → 先确认新数字是从板上量出来的，
再一起改这里的常量，并在 CHANGELOG 记一句。
"""
import json
import os
import re
from collections import Counter
from pathlib import Path

import pytest

from conftest import ROOT, EXAMPLES, TEMPLATE, run

# 华文行楷是商业字体，只在本机有（P5.3 会换成 OFL 字体，到时要连数字一起改）
FONT = Path(r"C:\Windows\Fonts\STXINGKA.TTF")

SPEC = EXAMPLES / "uestc70" / "spec.json"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if not FONT.exists():
        pytest.skip("本机没有 STXINGKA.TTF（商业字体，用户自备）")
    if not (SPEC.parent / json.loads(SPEC.read_text(encoding="utf-8"))["badge"]["png"]).exists():
        pytest.skip("缺徽记源图（校徽不在 MIT 内，可自行删除或替换，见 examples/uestc70/LOGO-COPYRIGHT.md）")
    # 故意给一个还不存在的嵌套目录：外人照 README 跑 out/xxx 时不能 FileNotFound
    out = tmp_path_factory.mktemp("rebuild") / "out" / "deep" / "PCB1.epcb2"
    r = run("16-build_board.py", SPEC, TEMPLATE, out)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = [l for l in out.read_text(encoding="utf-8").split("\n") if l.strip()]
    return r.stdout, lines


def test_record_count(built):
    _, lines = built
    assert len(lines) == 37571


def test_type_counts(built):
    _, lines = built
    c = Counter(re.search(r'"type":"([^"]+)"', l).group(1) for l in lines)
    assert c["FILL"] == 37408
    assert c["PAD"] == 9        # 主孔 φ3.0 + 参考板那圈 8×φ0.305
    assert c["STRING"] == 3     # 正/背 1956—2026 + 底部英文
    assert c["POLY"] == 5       # 板框 + 四圈金带（正铜/正窗/背铜/背窗）


def test_fill_per_layer(built):
    _, lines = built
    c = Counter()
    for l in lines:
        if '"type":"FILL"' in l:
            c[int(re.search(r'"layerId":(\d+)', l).group(1))] += 1
    assert c[1] == 16211   # 正面铜：织纹 + 徽记 + 校名
    assert c[2] == 8111    # 背面铜：织纹 + 校训
    assert c[4] == 262     # 底层丝印：底部英文
    assert c[5] == 10462   # 正面开窗：徽记 + 校名
    assert c[6] == 2362    # 背面开窗：校训


def test_stdout_stats(built):
    """条数对、面积不对 = 规格被人改了；两个都要锁。"""
    stdout, _ = built
    m = re.search(r"weave\s+(\d+) rects\s+([\d.]+) mm2", stdout)
    assert m, stdout
    assert int(m.group(1)) == 5749
    assert abs(float(m.group(2)) - 2239.0) < 5.0
    m = re.search(r"badge\s+(\d+) rects\s+([\d.]+) mm2", stdout)
    assert m, stdout
    assert abs(float(m.group(2)) - 465.3) < 2.5


def test_spec_badge_path_is_relative():
    """例子必须自带徽记图且用相对路径，否则别人 clone 下来跑到一半才报 FileNotFound。"""
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    png = spec["badge"]["png"]
    assert not os.path.isabs(png)
    if not (SPEC.parent / png).exists():
        pytest.skip("徽记图不在（可删可换，见 examples/uestc70/LOGO-COPYRIGHT.md）")
