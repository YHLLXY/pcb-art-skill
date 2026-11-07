# -*- coding: utf-8 -*-
"""自检脚本本身也要被测：它红/绿判反了，前面所有数字都白测。

用 examples/uestc70/gerber.zip 当金板（这块板交付时是全绿）。
"""
import pytest

from conftest import EXAMPLES, run

GERBER = EXAMPLES / "uestc70" / "gerber.zip"


@pytest.fixture(scope="module")
def checked():
    r = run("13-check.py", GERBER, "--board", "86.25x54.25", "--weave")
    return r


def test_no_fail(checked):
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "FAIL" not in checked.stdout


def test_known_numbers(checked):
    # 2026-11-07：04-gerber_raster 改成"弧线每个折点都画圆"（PIL 宽线不补接头）后，
    # 金带圆角的缺口被补上，这块板的沉金从 22.46% 变成 22.50%（面积 1049.94 -> 1052.15）。
    # 新数字才是对的：旧的那次把圆角的缺口也当成"没有铜"量掉了。
    out = checked.stdout
    assert "22.50%" in out          # 沉金（正金∪背金 ÷ 板框）
    assert "1052.15" in out         # 面积
    assert "100.0%" in out          # 织纹吻合度
    assert "0.120" in out           # 最小铜宽 p5
    assert "全绿" in out


def test_bad_board_is_red(tmp_path):
    """拿一块空板（只有板框）必须报 FAIL：证明退出码不是写死的 0。"""
    import zipfile
    z = tmp_path / "empty.zip"
    src = zipfile.ZipFile(GERBER)
    with zipfile.ZipFile(z, "w") as out:
        for n in src.namelist():
            if "BoardOutline" in n or n.upper().endswith(".GKO"):
                out.writestr(n, src.read(n))
    r = run("13-check.py", z, "--board", "86.25x54.25")
    assert r.returncode == 1, r.stdout
    assert "FAIL" in r.stdout
