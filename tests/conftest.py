# -*- coding: utf-8 -*-
"""测试共用的路径与调用工具。跑法：在仓库根目录 python -m pytest tests -q"""
import importlib.util
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EXAMPLES = ROOT / "examples"
TEMPLATE = ROOT / "templates" / "blank"

def run(script, *args, timeout=600):
    """跑 skill 里的脚本，返回 CompletedProcess（stdout/stderr 已按 utf-8 解）。"""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)

def load(name, filename):
    """脚本文件名带连字符和数字前缀，不能直接 import，用 importlib 按文件加载。"""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
