# -*- coding: utf-8 -*-
import re,sys,math
from PIL import Image, ImageDraw
src=sys.argv[1]; out=sys.argv[2]
import os
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
SC=float(os.environ.get("GR_SC","20"))
X0=float(os.environ.get("GR_X0","-46.0")); Y0=float(os.environ.get("GR_Y0","31.0"))
BW=float(os.environ.get("GR_W","92")); BH=float(os.environ.get("GR_H","62"))
def to_px(x,y): return ((x-X0)*SC,(Y0-y)*SC)
W,H=int(BW*SC),int(BH*SC)
txt=open(src,encoding='utf-8',errors='ignore').read()
aps={}
for m in re.finditer(r'%ADD(\d+)([A-Za-z]+),([-0-9.X]+)\*%', txt):
    aps[m.group(1)]=(m.group(2),[float(v) for v in m.group(3).split('X')])
im=Image.new('L',(W,H),0); dr=ImageDraw.Draw(im)
num=lambda v:int(v)/100000.0
X=Y=0.0; ap=None; region=False; pts=[]; mode=1
for ln in txt.split('\n'):
    ln=ln.strip()
    if not ln: continue
    if ln.startswith('G36'): region=True; pts=[]; continue
    if ln.startswith('G37'):
        if len(pts)>=6: dr.polygon([(px,py) for px,py in zip(pts[0::2],pts[1::2])],fill=255)
        region=False; pts=[]; continue
    m=re.match(r'^G54D(\d+)\*$',ln)
    if m: ap=aps.get(m.group(1)); continue
    g=1
    mg=re.match(r'^G0?([123])',ln)
    if mg: g=int(mg.group(1))
    m=re.match(r'^(?:G0?[123])?X?(-?\d*)Y?(-?\d*)?I(-?\d+)J(-?\d+)D0?([123])\*$',ln)
    arc=m is not None
    if not arc:
        m=re.match(r'^(?:G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?D0?([123])\*$',ln)
        if not m: continue
        nx=num(m.group(1)) if m.group(1) else X
        ny=num(m.group(2)) if m.group(2) else Y
        d=int(m.group(3))
        if region:
            pts+=to_px(nx,ny)
        elif d==1 and ap:
            wpx=max(1,int(round(ap[1][0]*SC)))
            p0=to_px(X,Y); p1=to_px(nx,ny)
            dr.line([p0,p1],fill=255,width=wpx)
            r0=wpx/2.0
            for (px,py) in (p0,p1):
                dr.ellipse([px-r0,py-r0,px+r0,py+r0],fill=255)
        elif d==3 and ap:
            cxp,cyp=to_px(nx,ny); r0=ap[1][0]/2*SC
            if ap[0]=='C': dr.ellipse([cxp-r0,cyp-r0,cxp+r0,cyp+r0],fill=255)
            elif ap[0]=='R': dr.rectangle([cxp-r0,cyp-r0,cxp+r0,cyp+r0],fill=255)
            elif ap[0]=='O': dr.ellipse([cxp-r0,cyp-r0,cxp+r0,cyp+r0],fill=255)
        X,Y=nx,ny
        continue
    nx=num(m.group(1)) if m.group(1) else X
    ny=num(m.group(2)) if m.group(2) else Y
    cx=X+num(m.group(3)); cy=Y+num(m.group(4))
    d=int(m.group(5))
    r=math.hypot(X-cx,Y-cy)
    a0=math.atan2(Y-cy,X-cx); a1=math.atan2(ny-cy,nx-cx)
    if g==2:
        while a1>=a0: a1-=2*math.pi
    else:
        while a1<=a0: a1+=2*math.pi
    # 段数按弧长定，别用固定 24 段：r=0.5 的小圆角会糊，r=30 的大弧会折
    n=max(8,int(abs(a1-a0)*r*SC/3.0)); path=[]
    for i in range(n+1):
        a=a0+(a1-a0)*i/n
        path.append(to_px(cx+r*math.cos(a),cy+r*math.sin(a)))
    if region:
        for p in path: pts+=p
    elif ap:
        wpx=max(1,int(round(ap[1][0]*SC)))
        dr.line(path,fill=255,width=wpx)
        r0=wpx/2.0
        # PIL 的宽多段线**不补接头**：只在首尾画圆，折点处会留下扇形缺口
        # （金带的圆角会被看成"锯齿"、最小线宽会被量成 0.02）。每个折点都要画圆。
        for (px,py) in path:
            dr.ellipse([px-r0,py-r0,px+r0,py+r0],fill=255)
    X,Y=nx,ny
im.save(out); print('saved',out)
