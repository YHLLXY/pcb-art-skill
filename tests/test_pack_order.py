# -*- coding: utf-8 -*-
"""下单包清单：19-pack_order 是"最后一道人手环节"唯一的凭据，必须被测。"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SCRIPTS


def run(*a):
    return subprocess.run([sys.executable, str(SCRIPTS / '19-pack_order.py')] + [str(x) for x in a],
                          capture_output=True, text=True, encoding='utf-8', errors='replace')


def make_pkg(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    (d / 'gerber.zip').write_bytes(b'PK\x03\x04' + b'0' * 200)
    (d / 'v1_front3d.png').write_bytes(b'\x89PNG' + b'1' * 100)
    (d / '下单说明.txt').write_text('单板 86.25x54.25\n', encoding='utf-8')
    (d / '验收单.md').write_text('# 验收单\n', encoding='utf-8')
    return d


def test_manifest_then_verify(tmp_path):
    d = make_pkg(tmp_path / 'pkg')
    r = run(d, '--require', '下单说明,验收单')
    assert r.returncode == 0, r.stdout + r.stderr
    man = (d / 'MANIFEST.txt').read_text(encoding='utf-8')
    assert 'sha256' in man and '合计' not in man.split('#')[0]
    # 4 个文件各一行 + 5 行表头
    assert len([l for l in man.splitlines() if l and not l.startswith('#')]) == 4
    assert 'MANIFEST.txt' not in man          # 清单不把自己列进去

    r = run(d, '--verify')
    assert r.returncode == 0, r.stdout
    assert '一致' in r.stdout


def test_verify_catches_tampering(tmp_path):
    d = make_pkg(tmp_path / 'pkg')
    assert run(d).returncode == 0
    (d / 'gerber.zip').write_bytes(b'PK\x03\x04TAMPERED')      # 换了一个字节都不行
    r = run(d, '--verify')
    assert r.returncode == 1
    assert '内容不一致' in r.stdout


def test_missing_required_file_fails(tmp_path):
    d = make_pkg(tmp_path / 'pkg')
    r = run(d, '--require', '下单说明,验收单,不存在的文件')
    assert r.returncode == 1
    assert '缺少必需文件' in r.stdout


def test_extra_file_after_verify_fails(tmp_path):
    d = make_pkg(tmp_path / 'pkg')
    assert run(d).returncode == 0
    (d / 'late_add.png').write_bytes(b'\x89PNG')
    r = run(d, '--verify')
    assert r.returncode == 1
    assert '清单没有' in r.stdout
