
# -*- coding: utf-8 -*-
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT=r"E:\homework\个人发展\生日礼物准备\李欣雨"
OUT=os.path.join(ROOT,"preview","v9"); os.makedirs(OUT,exist_ok=True)
K=0.0254
S=60.0            # px per mm
X0,X1=-17.0,17.0
Y0,Y1=5.0,26.0
W=int((X1-X0)*S); H=int((Y1-Y0)*S)
def to_px(x,y): return ((x-X0)*S,(Y1-y)*S)

CH="四川农业大学"
R_mm=484*K            # 12.29 mm
CY=8.6
FS_mm=74*K            # 1.88 mm
ROTS=[27.5,16.5,5.5,-5.5,-16.5,-27.5]
FONT=r"C:\Windows\Fonts\simsun.ttc"

canvas=Image.new("L",(W,H),0)
for ch,rot in zip(CH,ROTS):
    px=int(FS_mm*S*1.7)
    tile=Image.new("L",(px,px),0)
    f=ImageFont.truetype(FONT,int(FS_mm*S))
    d=ImageDraw.Draw(tile)
    b=d.textbbox((0,0),ch,font=f)
    d.text(((px-(b[2]-b[0]))/2-b[0],(px-(b[3]-b[1]))/2-b[1]),ch,font=f,fill=255)
    tile=tile.rotate(-rot,resample=Image.BICUBIC,expand=False)
    a=math.radians(rot)
    cx=-R_mm*math.sin(a); cy=CY+R_mm*math.cos(a)
    p=to_px(cx,cy)
    canvas.paste(Image.fromarray(np.maximum(np.asarray(canvas.crop((int(p[0]-px/2),int(p[1]-px/2),int(p[0]-px/2)+px,int(p[1]-px/2)+px))),np.asarray(tile))),(int(p[0]-px/2),int(p[1]-px/2)))
canvas.save(os.path.join(OUT,"arc.png"))
# preview composite with rings
prev=Image.new("RGB",(W,H),(16,16,18))
a=np.asarray(canvas)>127
prev.paste((214,170,90),(0,0),Image.fromarray((a*255).astype(np.uint8)))
prev.save(os.path.join(OUT,"arc-preview.png"))
print("canvas",canvas.size)
