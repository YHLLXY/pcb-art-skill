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
    # 这个数改过两次，两次都是"口径变准"，不是板子变：
    #   22.46%  原始：04-gerber_raster 的弧线折点没补圆，圆角金带的缺口被当成"没有铜"
    #   22.50%  修了光栅化器之后
    #   22.68%  分母从"外接框"改成"轮廓面积"（菱形/异形板必须这样，见 04 第 127 条）
    #   22.48%  织纹按官方样板改准（0.2225/0.115）后示例板重新导出，板框量到 4661 mm²
    out = checked.stdout
    assert "22.48%" in out          # 沉金（正金∪背金 ÷ 轮廓面积）
    assert "1051.04" in out         # 金面积
    assert "4661" in out            # 板面积按轮廓算
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
