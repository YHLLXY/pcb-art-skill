
# -*- coding: utf-8 -*-
import numpy as np, os
from PIL import Image, ImageDraw, ImageFont
import sys

try:                                    # Windows 控制台默认 GBK，中文表会变乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT=r"E:\homework\开发\嘉立创电路板开发\skill测试"
OUT=os.path.join(ROOT,"gen2"); os.makedirs(OUT,exist_ok=True)
K=0.0254
# 华文行楷是商业字体，仅本机自带；换 OFL 字体见 references/02「字体可以换」
FX=r"C:\Windows\Fonts\STXINGKA.TTF"; FT=r"C:\Windows\Fonts\times.ttf"
_M=ImageDraw.Draw(Image.new("L",(8,8),0))
def fit_px(s,fp,target_px,sp=0.0,vertical=False):
    n=len(s); px=max(6,int(target_px/(n*0.95+sp*(n-1))))
    for _ in range(5):
        f=ImageFont.truetype(fp,px)
        if vertical: tot=sum(_M.textbbox((0,0),c,font=f)[3]-_M.textbbox((0,0),c,font=f)[1] for c in s)+px*sp*(n-1)
        else: tot=sum(_M.textlength(c,font=f) for c in s)+px*sp*(n-1)
        if tot<=0: break
        px=max(6,int(px*target_px/tot))
    return px
def mask_row(s,fp,width_mm,sp=0.10):
    PX=fit_px(s,fp,width_mm*40,sp)
    f=ImageFont.truetype(fp,PX)
    wid=[_M.textlength(c,font=f) for c in s]; gap=PX*sp
    tot=sum(wid)+gap*(len(s)-1)
    im=Image.new("L",(int(tot)+40,PX*2+40),0); dr=ImageDraw.Draw(im); x=20
    for c,w in zip(s,wid):
        dr.text((x,20),c,font=f,fill=255); x+=w+gap
    return im.crop(im.getbbox())
def mask_col(s,fp,height_mm,sp=0.20):
    PX=fit_px(s,fp,height_mm*40,sp,vertical=True)
    f=ImageFont.truetype(fp,PX)
    gaps=PX*sp; tot=PX*len(s)+gaps*(len(s)-1)
    im=Image.new("L",(PX*2+40,int(tot)+40),0); dr=ImageDraw.Draw(im); y=20
    for c in s:
        b=_M.textbbox((0,0),c,font=f)
        dr.text((20+(PX-(b[2]-b[0]))/2-b[0], y-b[1]),c,font=f,fill=255)
        y+=(b[3]-b[1])+gaps
    return im.crop(im.getbbox())
def scan(img,w_mm,cx,cy,step=0.06,minw=0.15,hfac=1.25,mirror=False):
    a=np.asarray(img)>127; H,W=a.shape
    s=w_mm/W; TH=H*s; rows=int(round(TH/step)); xl=cx-w_mm/2.0; yt=cy+TH/2.0; out=[]
    for r in range(rows):
        py=int(((r+0.5)*step)/s)
        if py<0 or py>=H: continue
        idx=np.nonzero(a[py])[0]
        if len(idx)==0: continue
        runs=[];st=idx[0];pv=idx[0]
        for v in idx[1:]:
            if v==pv+1: pv=v
            else: runs.append((st,pv)); st=v; pv=v
        runs.append((st,pv))
        yc=yt-(r+0.5)*step
        for (s0,s1) in runs:
            x0=xl+s0*s; x1=xl+(s1+1)*s
            if x1-x0<minw: x1=x0+minw
            w=x1-x0; left=x0 if not mirror else -(x0+w)
            out.append((left,yc+step/2.0,w,step*hfac))
    return out
def emit(name,layer,rs,chunk=500):
    n=0
    for i in range(0,len(rs),chunk):
        body=",".join("[%s,%s,%s,%s]"%(round(a/K,1),round(b/K,1),round(c/K,1),round(d/K,1)) for (a,b,c,d) in rs[i:i+chunk])
        js=("const M=eda.pcb_MathPolygon,F=eda.pcb_PrimitiveFill;const D=[%s];"
            "for(const d of D){await(F.create(%d,M.createPolygon(['R',d[0],d[1],d[2],d[3],0,0]),'',0,0,false));}"
            "await(eda.pcb_Document.save());return 'ok '+D.length;"%(body,layer))
        open(os.path.join(OUT,"%s_%02d.js"%(name,i//chunk)),"w",encoding="utf-8").write(js); n+=1
    print("%-6s L%-2d %5d rects %2d files"%(name,layer,len(rs),n))
def grow(rs,g=0.10): return [(l-g/2,y+g/2,w+g,h+g) for (l,y,w,h) in rs]

# back motto (MIRRORED)
m=mask_row("修德博学",FX,33.0,0.16); MT=scan(m,33.0,0.0,4.2,mirror=True)
m=mask_row("求实创新",FX,33.0,0.16); MT+=scan(m,33.0,0.0,-6.2,mirror=True)
emit("mt2",2,MT); emit("mt6",6,grow(MT))
# back 1950 + CQUPT line (both MIRRORED, on copper + bottom silk)
m=mask_row("1950",FT,12.0,0.0); YR=scan(m,12.0,0.0,-14.2,mirror=True)
emit("yr2",2,YR); emit("yr6",6,grow(YR))
m=mask_row("CQUPT · CHONGQING · CHINA",FT,26.0,0.0); CP=scan(m,26.0,0.0,-19.6,minw=0.15,mirror=True)
emit("cp4",4,CP)
# front columns swapped (修德左, 求实右)
CL=[]
m=mask_col("修德博学",FX,13.5,0.20); CL+=scan(m,13.5*m.width/m.height,-32.8,16.4)
m=mask_col("求实创新",FX,13.5,0.20); CL+=scan(m,13.5*m.width/m.height,32.8,16.4)
emit("cl1",1,CL); emit("cl5",5,grow(CL))
