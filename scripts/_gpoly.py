# -*- coding: utf-8 -*-
"""板框轮廓解析（13-check / 14-render3d 共用）。

板框在 Gerber 里是一条**首尾相接的描边路径**（线 + 圆弧），不是多边形区域。
把它解析成点列之后：shoelace 给准确面积，polygon 填充给掩膜——
菱形/异形板才不会退化成"外接框"。
"""
import math
import re


def polygon(path, seg_per_mm=4.0, max_seg=720):
    """返回 [(x_mm, y_mm), ...]（不闭合，首尾相接）。单位按 mm（FSLAX45Y45 + MOMM）。"""
    txt = open(path, encoding="utf-8", errors="ignore").read()
    X = Y = 0.0
    pts = []
    g = 1
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("G04") or ln.startswith("%"):
            continue
        mg = re.match(r"^G0?([123])", ln)
        if mg:
            g = int(mg.group(1))
        m = re.match(r"^(?:G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?D0?([123])\*$", ln)
        if not m:
            continue
        nx = int(m.group(1)) / 100000.0 if m.group(1) else X
        ny = int(m.group(2)) / 100000.0 if m.group(2) else Y
        d = int(m.group(5))
        if d == 2:
            pts = [(nx, ny)]                      # 新的轮廓起点
        elif d in (1, 3):
            if m.group(3) or m.group(4):
                cx = X + (int(m.group(3)) / 100000.0 if m.group(3) else 0.0)
                cy = Y + (int(m.group(4)) / 100000.0 if m.group(4) else 0.0)
                rr = math.hypot(X - cx, Y - cy)
                a0 = math.atan2(Y - cy, X - cx)
                a1 = math.atan2(ny - cy, nx - cx)
                if g == 2:
                    while a1 >= a0:
                        a1 -= 2 * math.pi
                else:
                    while a1 <= a0:
                        a1 += 2 * math.pi
                n = min(max_seg, max(8, int(abs(a1 - a0) * rr * seg_per_mm)))
                for i in range(1, n + 1):
                    a = a0 + (a1 - a0) * i / n
                    pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
            else:
                pts.append((nx, ny))
        X, Y = nx, ny
    return pts


def area_mm2(pts):
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0
