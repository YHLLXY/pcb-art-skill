
# -*- coding: utf-8 -*-
"""14-render3d.py  —— 用 Gerber 各层做一张"像照片"的 3D 预览（无需 EDA 3D 视图）

原理：把铜/丝印当高度场 -> 法线 -> 定向光 + 半球光 + 金属高光。
哑黑阻焊：低反射、弱高光；沉金：金属色 + 强高光 + 边缘补光；白丝印：漫反射。

用法:
  python 14-render3d.py <gerber目录> <输出前缀> [--sc 30] [--angle 0]
输出:
  <前缀>_front3d.png / <前缀>_back3d.png
"""
import os, sys, subprocess, tempfile, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ARGV = sys.argv[1:]
def opt(name, default):
    if name in ARGV:
        i = ARGV.index(name); v = ARGV[i+1]; del ARGV[i:i+2]; return v
    return default
D   = ARGV[0]
PFX = ARGV[1]
SC  = float(opt("--sc", "30"))
HERE = os.path.dirname(os.path.abspath(__file__))
RAST = os.path.join(HERE, "04-gerber_raster.py")

PATS = [("GTL",["TopLayer","F_Cu"]),("GBL",["BottomLayer","B_Cu"]),
        ("GTS",["TopSolderMask","F_Mask"]),("GBS",["BottomSolderMask","B_Mask"]),
        ("GTO",["TopSilkscreen","F_Silk"]),("GBO",["BottomSilkscreen","B_Silk"]),
        ("GKO",["BoardOutline","Edge_Cuts"])]
SRC = {}
files = os.listdir(D)
for k, keys in PATS:
    for f in files:
        if any(kk.lower() in f.lower() for kk in keys):
            SRC[k] = os.path.join(D, f); break
    else:
        SRC[k] = None

def L(k, sc, x0, y0, w, h):
    if not SRC.get(k): return None
    out = os.path.join(tempfile.gettempdir(), "r3_%s_%d.png" % (k, int(sc)))
    env = dict(os.environ); env["GR_SC"] = str(sc)
    env["GR_X0"] = "%.4f" % x0; env["GR_Y0"] = "%.4f" % y0
    env["GR_W"] = "%.4f" % w; env["GR_H"] = "%.4f" % h
    subprocess.run([sys.executable, RAST, SRC[k], out], check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return np.array(Image.open(out).convert("L")) > 128

# 先在大窗口里定位板框（mm），再按 SC 精确重栅格化
gko0 = L("GKO", 10, -100, 100, 200, 200)
ys, xs = np.nonzero(gko0)
bx0 = -100 + xs.min()/10.0; bx1 = -100 + xs.max()/10.0
by1 = 100 - ys.min()/10.0;  by0 = 100 - ys.max()/10.0
MARGIN = 6.0
X0, Y0 = bx0-MARGIN, by1+MARGIN
W, H = (bx1-bx0)+2*MARGIN, (by1-by0)+2*MARGIN
m = {k: L(k, SC, X0, Y0, W, H) for k in SRC}
h, w = m["GKO"].shape
def px(x, y): return ((x-X0)*SC, (Y0-y)*SC)
board = Image.new("L", (w, h), 0)
a0 = px(bx0, by1); a1 = px(bx1, by0)
ImageDraw.Draw(board).rounded_rectangle((a0[0], a0[1], a1[0], a1[1]), radius=int(3.5*SC), fill=255)
board = np.asarray(board) > 0

def shade(cu, op, silk, name):
    cuM   = (cu if cu is not None else np.zeros_like(board)) & board
    opM   = (op if op is not None else np.zeros_like(board)) & board
    silkM = (silk if silk is not None else np.zeros_like(board)) & board
    gold  = cuM & opM
    white = silkM & ~gold
    black = board & ~gold & ~white
    # 高度场：铜 35um，丝印 20um，开窗处下沉（凹陷）1.5um
    Hf = (cuM.astype(np.float32)*0.035) + (silkM.astype(np.float32)*0.020)
    Hf = Hf - (opM & ~cuM).astype(np.float32)*0.004
    # 轻度平滑，避免单像素噪声
    Hi = Image.fromarray(((Hf/Hf.max())*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2))
    Hf = np.asarray(Hi).astype(np.float32)/255.0
    gy, gx = np.gradient(Hf)
    k = 140.0                      # 浮雕强度
    nx, ny, nz = -gx*k, -gy*k, np.ones_like(Hf)
    nn = np.sqrt(nx*nx+ny*ny+nz*nz); nx/=nn; ny/=nn; nz/=nn
    Ldir = np.array([-0.45, 0.55, 0.70]); Ldir /= np.linalg.norm(Ldir)
    V = np.array([0.0, 0.0, 1.0])
    Hh = (Ldir+V); Hh /= np.linalg.norm(Hh)
    ndl = np.clip(nx*Ldir[0]+ny*Ldir[1]+nz*Ldir[2], 0, 1)
    ndh = np.clip(nx*Hh[0]+ny*Hh[1]+nz*Hh[2], 0, 1)
    # 半球光（顶部亮、底部暗），模拟柔光箱
    yy = np.linspace(1, -1, h)[:, None]*np.ones((1, w))
    hemi = 0.55 + 0.45*(0.5+0.5*yy)
    img = np.zeros((h, w, 3), np.float32)
    # 哑黑阻焊
    base = np.array([0.035, 0.035, 0.040])
    img += black[..., None]*(base*(0.35+0.65*ndl[..., None]*hemi[..., None])
                             + 0.02*np.clip(ndh, 0, 1)[..., None]**40)
    # 沉金
    gold_c = np.array([0.83, 0.66, 0.30])
    spec = np.clip(ndh, 0, 1)**22
    img += gold[..., None]*(gold_c*(0.30+0.70*ndl[..., None]*hemi[..., None])
                            + 0.95*spec[..., None])
    # 白丝印
    wc = np.array([0.93, 0.93, 0.90])
    img += white[..., None]*(wc*(0.66+0.34*ndl[..., None]*hemi[..., None])
                             + 0.06*np.clip(ndh, 0, 1)[..., None]**30)
    # 板外：背景 + 投影
    sh = Image.fromarray((board*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(int(1.6*SC)))
    shadow = (np.asarray(sh).astype(np.float32)/255.0)**0.6
    bg = np.array([0.085, 0.085, 0.090])
    out = img.copy()
    out[~board] = bg*(1 - 0.55*shadow[~board][:, None])
    # 板边高光（0.25mm 倒角）
    edge = board & ~np.asarray(Image.fromarray((board*255).astype(np.uint8))
                               .filter(ImageFilter.MinFilter(5))).astype(bool)
    out[edge] = out[edge]*0.55 + 0.12
    img8 = (np.clip(out, 0, 1)**(1/1.05)*255).astype(np.uint8)
    Image.fromarray(img8).save(name)
    print("saved", name, "gold %.2f%% silk %.2f%%" % (100*gold.sum()/board.sum(), 100*white.sum()/board.sum()))

shade(m["GTL"], m["GTS"], m["GTO"], PFX + "_front3d.png")
shade(m["GBL"], m["GBS"], m["GBO"], PFX + "_back3d.png")
